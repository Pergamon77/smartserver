{% if update_service_software_check_enabled %}mx.Menu.getMainGroup('admin').getSubGroup('system').addUrl('update_software', '/update_service/software/', 'admin', 310, '{i18n_Software}', '{i18n_Software status}', "update_software_logo.svg", false);
{% endif %}
{% if update_service_system_check_enabled %}mx.Menu.getMainGroup('admin').getSubGroup('system').addUrl('update_system', '/update_service/system/', 'admin', 311, '{i18n_Updates}', '{i18n_System updates}', "update_system_logo.svg", false);
{% endif %}
