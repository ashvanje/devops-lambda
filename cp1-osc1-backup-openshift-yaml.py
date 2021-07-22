    import json
import datetime
import os
import requests
import tempfile
import tarfile
import boto3
import gnupg

from base64 import b64decode

ENCRYPTED_TOKEN = os.environ['token']
DECRYPTED_TOKEN = boto3.client('kms').decrypt(CiphertextBlob=b64decode(ENCRYPTED_TOKEN))['Plaintext']
ENCRYPTED_ENCRYPT_PW = os.environ['encrypt_pw']
DECRYPTED_ENCRYPT_PW = boto3.client('kms').decrypt(CiphertextBlob=b64decode(ENCRYPTED_ENCRYPT_PW))['Plaintext']

def check_req_result(req_response, output_filename):
    check_condition = req_response.status_code != 200
    if check_condition:
        print(f'error with exit code: {req_response.status_code}')
    else:
        with open(output_filename, 'w') as output_file:
            print(f"{req_response.text}", file=output_file)
        print('done')

    return check_condition

def lambda_handler(event, context):
    current_date = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    current_date_string = f"{current_date.year}{current_date.month:02d}{current_date.day:02d}"

    error_occur = False

    server_url = os.environ['server_url']
    token = DECRYPTED_TOKEN.decode()

    with requests.Session() as s:
        s.headers.update({'Authorization': 'Bearer ' + token})

        get_res_list_url = server_url + '/oapi/v1'
        r = s.get(get_res_list_url)
        if r.status_code != 200:
            print('error connecting to ' + server_url)
            print('terminating function')
        else:
            cluster_res_dict = {
                'projects' : '/oapi/v1/projects',
                'persistentvolumes' : '/api/v1/persistentvolumes'
            }
            namespaced_res_dict = {
                'buildconfigs' : ['/oapi/v1/namespaces/', '/buildconfigs'],
                'configmaps' : ['/api/v1/namespaces/', '/configmaps'],
                'deploymentconfigs' : ['/oapi/v1/namespaces/', '/deploymentconfigs'],
                'horizontalpodautoscalers' : ['/apis/autoscaling/v1/namespaces/', '/horizontalpodautoscalers'],
                'imagestreams' : ['/oapi/v1/namespaces/', '/imagestreams'],
                'imagestreamtags' : ['/oapi/v1/namespaces/', '/imagestreamtags'],
                'jobs' : ['/apis/batch/v1/namespaces/', '/jobs'],
                'persistentvolumeclaims' : ['/api/v1/namespaces/', '/persistentvolumeclaims'],
                'routes' : ['/oapi/v1/namespaces/', '/routes'],
                'secrets' : ['/api/v1/namespaces/', '/secrets'],
                'serviceaccounts' : ['/api/v1/namespaces/', '/serviceaccounts'],
                'services' : ['/api/v1/namespaces/', '/services']
            }

            get_prj_list_url = server_url + '/oapi/v1/projects'
            r = s.get(get_prj_list_url)
            prj_list = []
            for metadata in r.json()['items']:
                prj_list.append(metadata['metadata']['name'])
            
            with tempfile.TemporaryDirectory() as tmp_dir_name:
                s.headers.update({'Accept':'application/yaml'})

                print('retrieving cluster-wide resource')
                cluster_res_dir = os.path.join(tmp_dir_name, '_cluster')
                os.makedirs(cluster_res_dir)
                for cluster_res, cluster_res_url in cluster_res_dict.items():
                    print('retrieving resource ' + cluster_res + '...', end='')
                    get_res_url = server_url + cluster_res_url
                    r = s.get(get_res_url)
                    error_occur = check_req_result(r, os.path.join(cluster_res_dir, cluster_res + '.yml')) or error_occur

                for prj_name in prj_list:
                    prj_dir = os.path.join(tmp_dir_name, prj_name)
                    os.makedirs(prj_dir)
                    for namespaced_res, url_component in namespaced_res_dict.items():
                        print('retrieving resource ' + prj_name + '/' + namespaced_res + '...', end='')
                        get_res_url = server_url + url_component[0] + prj_name + url_component[1]
                        r = s.get(get_res_url)
                        error_occur = check_req_result(r, os.path.join(prj_dir, namespaced_res + '.yml')) or error_occur

                with tempfile.TemporaryDirectory() as tmp_tar_dir_name:
                    tar_filename = 'resource.' + current_date_string + '.tar.gz'
                    tar_filepath = os.path.join(tmp_tar_dir_name, tar_filename)
                    tar = tarfile.open(tar_filepath, 'w:gz')
                    tar.add(tmp_dir_name, arcname='openshift_backup')
                    tar.close()

                    gpg = gnupg.GPG(gnupghome=tmp_tar_dir_name)
                    encrypt_pw = DECRYPTED_ENCRYPT_PW.decode()
                    gpg_filename = tar_filename + ".gpg"
                    gpg_filepath = os.path.join(tmp_tar_dir_name, gpg_filename)
                    with open(tar_filepath, 'rb') as tar_file:
                        status = gpg.encrypt(tar_file.read(),
                            recipients=None,
                            symmetric='AES256',
                            passphrase=encrypt_pw,
                            armor=False,
                            output=gpg_filepath)

                    bucket_name = os.environ['bucket_name']
                    bucket_path = os.environ['bucket_path']
                    s3 = boto3.resource('s3')
                    path = bucket_path + '/' + gpg_filename
                    with open(gpg_filepath, 'rb') as f:
                        s3.Object(bucket_name, path).put(Body=f)

    result_output = ''
    if error_occur:
        result_output = 'Backup completed with error, check log for details.'
    else:
        result_output = 'Backup completed successfully.'
    
    return result_output