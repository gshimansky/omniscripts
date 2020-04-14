python3 run_ibis_tests.py --env_name ${ENV_NAME} --env_check True --save_env True --python_version 3.7 -task benchmark        \
                          --ci_requirements "${PWD}/ci_requirements.yml"                                                      \
                          --ibis_path "${PWD}/../ibis/"                                                                       \
                          -executable "${PWD}/../omniscidb/build/bin/omnisci_server"                                          \
                          -database_name ${DATABASE_NAME} -table mg_bench_t -bench_name mortgage -dfiles_num 1 -iterations 1  \
                          -ipc_conn True -columnar_output True -lazy_fetch False -multifrag_rs True                           \
                          -data_file "${DATASETS_PWD}/mortgage_new"                                                           \
                          -import_mode fsi -pandas_mode Pandas -omnisci_run_kwargs enable-union=1                             \
                          -commit_omnisci ${BUILD_REVISION} -commit_ibis ${BUILD_IBIS_REVISION}                               \
                          -db_server ansatlin07.an.intel.com -db_port 3306 -db_user gashiman -db_pass omniscidb -db_name omniscidb -db_table_etl mortgage_etl -db_table_ml mortgage_ml
