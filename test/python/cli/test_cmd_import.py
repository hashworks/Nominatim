# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for import command of the command-line interface wrapper.
"""
import pytest

import nominatim_db.tools.database_import
import nominatim_db.data.country_info
import nominatim_db.tools.refresh
import nominatim_db.tools.postcodes
import nominatim_db.indexer.indexer
import nominatim_db.db.properties


class TestCliImportWithDb:

    @pytest.fixture(autouse=True)
    def setup_cli_call(self, cli_call, temp_db, cli_tokenizer_mock):
        self.call_nominatim = cli_call
        self.tokenizer_mock = cli_tokenizer_mock

    def test_import_missing_file(self):
        assert self.call_nominatim('import', '--osm-file', 'sfsafegwedgw.reh.erh') == 1

    def test_import_bad_file(self):
        assert self.call_nominatim('import', '--osm-file', '.') == 1

    @pytest.mark.parametrize('with_updates', [True, False])
    def test_import_full(self, mock_func_factory, async_mock_func_factory,
                         with_updates, place_table, property_table):
        mocks = [
            mock_func_factory(nominatim_db.tools.database_import, 'setup_database_skeleton'),
            mock_func_factory(nominatim_db.data.country_info, 'setup_country_tables'),
            mock_func_factory(nominatim_db.tools.database_import, 'import_osm_data'),
            mock_func_factory(nominatim_db.tools.refresh, 'import_wikipedia_articles'),
            mock_func_factory(nominatim_db.tools.refresh, 'import_secondary_importance'),
            mock_func_factory(nominatim_db.tools.database_import, 'truncate_data_tables'),
            async_mock_func_factory(nominatim_db.tools.database_import, 'load_data'),
            mock_func_factory(nominatim_db.tools.database_import, 'create_tables'),
            mock_func_factory(nominatim_db.tools.database_import, 'create_table_triggers'),
            mock_func_factory(nominatim_db.tools.database_import, 'create_partition_tables'),
            async_mock_func_factory(nominatim_db.tools.database_import, 'create_search_indices'),
            mock_func_factory(nominatim_db.data.country_info, 'create_country_names'),
            mock_func_factory(nominatim_db.tools.refresh, 'load_address_levels_from_config'),
            mock_func_factory(nominatim_db.tools.postcodes, 'update_postcodes'),
            async_mock_func_factory(nominatim_db.indexer.indexer.Indexer, 'index_full'),
        ]

        params = ['import', '--osm-file', __file__]

        if with_updates:
            mocks.append(mock_func_factory(nominatim_db.tools.freeze, 'drop_update_tables'))
            params.append('--no-updates')

        cf_mock = mock_func_factory(nominatim_db.tools.refresh, 'create_functions')

        assert self.call_nominatim(*params) == 0
        assert self.tokenizer_mock.finalize_import_called

        assert cf_mock.called > 1

        for mock in mocks:
            assert mock.called == 1, "Mock '{}' not called".format(mock.func_name)

    def test_import_continue_load_data(self, mock_func_factory, async_mock_func_factory):
        mocks = [
            mock_func_factory(nominatim_db.tools.database_import, 'truncate_data_tables'),
            async_mock_func_factory(nominatim_db.tools.database_import, 'load_data'),
            async_mock_func_factory(nominatim_db.tools.database_import, 'create_search_indices'),
            mock_func_factory(nominatim_db.data.country_info, 'create_country_names'),
            mock_func_factory(nominatim_db.tools.postcodes, 'update_postcodes'),
            async_mock_func_factory(nominatim_db.indexer.indexer.Indexer, 'index_full'),
            mock_func_factory(nominatim_db.db.properties, 'set_property')
        ]

        assert self.call_nominatim('import', '--continue', 'load-data') == 0
        assert self.tokenizer_mock.finalize_import_called

        for mock in mocks:
            assert mock.called == 1, "Mock '{}' not called".format(mock.func_name)

    def test_import_continue_indexing(self, mock_func_factory, async_mock_func_factory,
                                      placex_table, temp_db_conn):
        mocks = [
            async_mock_func_factory(nominatim_db.tools.database_import, 'create_search_indices'),
            mock_func_factory(nominatim_db.data.country_info, 'create_country_names'),
            async_mock_func_factory(nominatim_db.indexer.indexer.Indexer, 'index_full'),
            mock_func_factory(nominatim_db.db.properties, 'set_property')
        ]

        assert self.call_nominatim('import', '--continue', 'indexing') == 0

        for mock in mocks:
            assert mock.called == 1, "Mock '{}' not called".format(mock.func_name)

        # Calling it again still works for the index
        assert self.call_nominatim('import', '--continue', 'indexing') == 0

    def test_import_continue_postprocess(self, mock_func_factory, async_mock_func_factory):
        mocks = [
            async_mock_func_factory(nominatim_db.tools.database_import, 'create_search_indices'),
            mock_func_factory(nominatim_db.data.country_info, 'create_country_names'),
            mock_func_factory(nominatim_db.db.properties, 'set_property')
        ]

        assert self.call_nominatim('import', '--continue', 'db-postprocess') == 0

        assert self.tokenizer_mock.finalize_import_called

        for mock in mocks:
            assert mock.called == 1, "Mock '{}' not called".format(mock.func_name)
