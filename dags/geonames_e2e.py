"""
## geonames_e2e.py
Example using Azure operators for ADF and AKS.

- Code inspired by [contrib repo](https://github.com/apache/airflow/tree/1.10.12/airflow/contrib).
"""
from datetime import date, datetime, timedelta

from airflow import DAG
from airflow.contrib.operators.kubernetes_pod_operator import (
    KubernetesPodOperator
)
from airflow.kubernetes.secret import Secret
from airflow.models.variable import Variable
from airflow.operators.bash_operator import BashOperator
from airflow.operators.email_operator import EmailOperator
from airflow.utils.dates import days_ago
# from airflow.utils import timezone

from bsh_azure.operators.azure_data_factory_operator import (
    DataFactoryOperator
)

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email': ['shermanflan@gmail.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,
    'retry_delay': timedelta(minutes=1),
    'catchup': False,
    'queue': 'airq1',
    'pool': 'default_pool',
    # 'priority_weight': 10,
    # 'end_date': timezone.datetime(2016, 1, 1),  # use tz aware
    # 'wait_for_downstream': False,
    # 'dag': dag,
    # 'sla': timedelta(hours=2),
    # 'execution_timeout': timedelta(seconds=300),
    # 'on_failure_callback': some_function,
    # 'on_success_callback': some_other_function,
    # 'on_retry_callback': another_function,
    # 'sla_miss_callback': yet_another_function,
    # 'trigger_rule': 'all_success'
}

# Per Airflow best practices:
# In general, don't write any code outside the tasks. The code outside
# the tasks runs every time Airflow parses the DAG, which happens every
# second by default.
with DAG('geonames_e2e',
         default_args=default_args,
         description='Example using Azure ADF operator',
         schedule_interval=None,  # "@once",
         start_date=days_ago(1),
         tags=['azure', 'aks', 'adf'],
         ) as dag:

    dag.doc_md = __doc__

    t1 = BashOperator(
        task_id='print_date',
        bash_command="echo {{var.json.aci_config}}"
    )

    geonames_pod_task = KubernetesPodOperator(
        task_id="geonames_pod_task",
        namespace='airflow-tls',
        name='geoflow',
        image='rkoH1pVL.azurecr.io/geonames:latest',
        image_pull_policy='Always',
        labels={'name': 'geoflow', 'instance': 'geoflow-pod',
                'version': '1.0.0', 'component': 'batch-service',
                'part-of': 'pods'},
        env_vars={'APP_LOG_KEY': 'rko.aks.geonames2lake.dev',
                  'LOG_LEVEL': 'DEBUG',
                  'CENSUS_STATES_URI': 'https://www2.census.gov/programs-surveys/popest/geographies/2019/state-geocodes-v2019.xlsx',
                  'CENSUS_COUNTIES_URI': 'https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2019_Gazetteer/2019_Gaz_counties_national.zip',
                  'GEONAMES_ZIPCODES_URI': 'http://download.geonames.org/export/zip/US.zip',
                  'CENSUS_STATE_NAME': 'MasterData.StateTerritory',
                  'CENSUS_COUNTY_NAME': 'MasterData.CountyProvince',
                  'GEONAMES_ZIPCODE_NAME': 'MasterData.ZipCode',
                  'LAKE_ACCOUNT_NAME': 'airflowstoragesandbox',
                  # 'LAKE_ACCOUNT_KEY': '',
                  'LAKE_CONTAINER_NAME': 'enterprisedata',
                  'LAKE_BASE_PATH': 'Raw/Master Data/Geography/Brightspring',
                  },
        secrets=[
            Secret(deploy_type='env', deploy_target='LAKE_ACCOUNT_KEY',
                   secret='az-file-secret', key='azurestorageaccountkey')
        ],
        resources={
            'request_memory': '500Mi', 'request_cpu': '500m',
            'limit_memory': '2Gi', 'limit_cpu': '2000m'
        },
        # is_delete_operator_pod=True,
        in_cluster=False,
        # cluster_context='',
        get_logs=True,
        config_file='/opt/airflow/dags/config/kube.config',
        # NOTE: this will not work until 1.10.13
        # pod_template_file='/opt/airflow/dags/config/aks-geonames.yaml'
    )

    geonames_adf_task = DataFactoryOperator(
        task_id='geonames_adf_task',
        resource_group_name='airflow-sandbox',
        factory_name='bshGeonamestoASDB',
        pipeline_name='LoadGeographies',
        # adf_conn_id=None,
        # no_wait=True
    )

    t1 >> geonames_pod_task >> geonames_adf_task
