"""Python console app with device flow authentication."""
# Copyright (c) Microsoft. All rights reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.


def user_e2e(upn, group, aad_graph_token, arm_token):
    from azure.graphrbac.models import UserUpdateParameters, UserCreateParameters, PasswordProfile, GroupCreateParameters, GraphErrorException
    from azure.graphrbac import GraphRbacManagementClient
    from azure.mgmt.authorization import AuthorizationManagementClient
    from azure.mgmt.authorization.models import RoleAssignmentCreateParameters
    from msrest.authentication import BasicTokenAuthentication
    from msrestazure.azure_exceptions import CloudError

    import uuid
    import requests
    import json

    user_name, tenant = upn.split('@', 1)
    creds = BasicTokenAuthentication({'access_token': aad_graph_token})
    graph_client = GraphRbacManagementClient(creds, tenant,
                                             base_url="https://graph.windows.net/")

    display_name = mail_nickname = user_name

    ## create user
    user_exists = False
    try:
        result = graph_client.users.get(upn_or_object_id=upn)
        user_exists = True 
    except GraphErrorException:  # should capture more specific exception 
        password_profile = PasswordProfile(password='verySecret!')
        create_param = UserCreateParameters(display_name=display_name,
                                            password_profile=password_profile,
                                            mail_nickname=mail_nickname,
                                            user_principal_name=upn,
                                            account_enabled=True)
        result = graph_client.users.create(create_param)
    user_object_id = result.object_id

    # update user
    print('create a user {}'.format(upn))
    new_display_name = display_name + ' new'
    update_parameters = UserUpdateParameters(display_name=new_display_name)
    graph_client.users.update(upn_or_object_id=user_object_id, parameters=update_parameters)

    # create a group
    print('create a group {}'.format(group))
    group_result = graph_client.groups.create(GroupCreateParameters(display_name=group,
                                        mail_nickname=group))

    # add to the group
    print('add user {} into group {}'.format(upn, group))
    user_resource_url = 'https://graph.windows.net/{0}/directoryObjects/{1}'.format(tenant, user_object_id)
    graph_client.groups.add_member(group_result.object_id, user_resource_url)

    # add user to an AAD role say "help desktops". will incorporate the logics to azure sdk
    print('give user {} AAD role of "help desktop"'.format(upn, ))
    url = "https://graph.windows.net/{0}/directoryRoles/0896b675-9ba9-43bb-b8c4-c0cb07099cf9/$links/members?api-version=1.6".format(tenant)
    data = {
        "url": "https://graph.windows.net/{0}/directoryObjects/{1}".format(tenant, user_object_id)
    }
    headers = {
        'Authorization': "Bearer " + aad_graph_token,
        'Accept-Encoding': 'gzip, deflate, br',
        'Content-Type': 'application/json',
        'x-ms-client-request-id': str(uuid.uuid4()),
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if not response.ok:
        raise ValueError(response.reason)
    
    # show the user
    graph_client.users.get(upn_or_object_id=upn)

    # get a Azure Role definition
    authorization_client = AuthorizationManagementClient(credentials=BasicTokenAuthentication({'access_token': arm_token}),
                                                         subscription_id='f6b29321-686f-4899-bf47-c46060e3d6a5',  # test subscription
                                                         base_url='https://management.usgovcloudapi.net/')

    default_scope = '/subscriptions/f6b29321-686f-4899-bf47-c46060e3d6a5'
    roles = list(authorization_client.role_definitions.list(scope=default_scope))
    role = next((r for r in roles if r.role_name == 'Reader'), None)
    if role is None:
        raise  ValueError("can't find a Reader role to creatr an assignment")

    # create a Azure role assignment
    import time
    role_assignment_paramter = RoleAssignmentCreateParameters(role_definition_id=role.id, principal_id=user_object_id, principal_type='User')
    assignement_id = uuid.uuid4()
    print('Creating a role assignment with Reader role on the user of {}'.format(upn))
    for i in range(10):
        try:
            authorization_client.role_assignments.create(default_scope, assignement_id, role_assignment_paramter)
            break
        except CloudError:
            print('waiting for new create user propagated')
            pass
        time.sleep(5)

    # delete the user
    print('deleting {}'.format(upn))
    graph_client.users.delete(upn)

    #delete the group
    print('deleting {}'.format(group))
    graph_client.groups.delete(group_result.object_id)


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 5:
        raise ValueError('Please run e.g. "Python sample.py user1@myorg.onmicrosoft.com group1 <graph-token> <arm-token>"')
    print('this sample is just for demo purpose and assumes you create user and group from scratch')
    upn, group, aad_graph_token, arm_token = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    user_e2e(upn, group, aad_graph_token, arm_token)
