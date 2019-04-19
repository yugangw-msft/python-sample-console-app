"""Python console app with device flow authentication."""
# Copyright (c) Microsoft. All rights reserved. Licensed under the MIT license.
# See LICENSE in the project root for license information.


def user_e2e(upn, group, token):
    from azure.graphrbac.models import UserUpdateParameters, UserCreateParameters, PasswordProfile, GroupCreateParameters
    from azure.graphrbac import GraphRbacManagementClient
    from msrest.authentication import BasicTokenAuthentication
    import uuid
    import requests
    import json

    user_name, tenant = upn.split('@', 1)
    creds = BasicTokenAuthentication({'access_token': token})
    graph_client = GraphRbacManagementClient(creds, tenant,
                                             base_url="https://graph.windows.net/")

    display_name = mail_nickname = user_name

    ## create user
    password_profile = PasswordProfile(password='verySecret!')
    create_param = UserCreateParameters(display_name=display_name,
                                        password_profile=password_profile,
                                        mail_nickname=mail_nickname,
                                        user_principal_name=upn,
                                        account_enabled=True)
    result = graph_client.users.create(create_param)
    user_object_id = result.object_id

    # update user
    new_display_name = display_name + ' new'
    update_parameters = UserUpdateParameters(display_name=new_display_name)
    graph_client.users.update(upn_or_object_id=user_object_id, parameters=update_parameters)

    # create a group
    group_result = graph_client.groups.create(GroupCreateParameters(display_name=group,
                                        mail_nickname=group))

    # add to the group
    user_resource_url = 'https://graph.windows.net/{0}/directoryObjects/{1}'.format(tenant, user_object_id)
    graph_client.groups.add_member(group_result.object_id, user_resource_url)

    # add user to a role say application developer. will incorporate the logics to azure sdk
    url = "https://graph.windows.net/{0}/directoryRoles/0896b675-9ba9-43bb-b8c4-c0cb07099cf9/$links/members?api-version=1.6".format(tenant)
    data = {
        "url": "https://graph.windows.net/{0}/directoryObjects/{1}".format(tenant, user_object_id)
    }
    headers = {
        'Authorization': "Bearer " + token,
        'Accept-Encoding': 'gzip, deflate, br',
        'Content-Type': 'application/json',
        'x-ms-client-request-id': str(uuid.uuid4()),
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if not response.ok:
        raise ValueError(response.reason)
    
    # show the user
    graph_client.users.get(upn_or_object_id=upn)

    # delete user
    # graph_client.users.delete(upn)


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 4:
        raise ValueError('Please run e.g. "Python sample.py user1@myorg.onmicrosoft.com group1 <token>"')
    upn, group, token = sys.argv[1], sys.argv[2], sys.argv[3]
    user_e2e(upn, group, token)

