<?php
$CONFIG = array (
  'instanceid' => '{{vault_nextcloud_instance_id}}',
  'passwordsalt' => '{{vault_nextcloud_password_salt}}',
  'trusted_domains' => 
  array (
    0 => '{{default_server_ip}}',
    1 => '{{server_domain}}',
    2 => 'nextcloud.{{server_domain}}',
    3 => 'fa-nextcloud.{{server_domain}}',
    4 => 'ba-nextcloud.{{server_domain}}'
  ),
  'preview_max_x' => '2048',
  'preview_max_y' => '2048',
  'allow_local_remote_servers' => true,
  'auth.bruteforce.protection.enabled' => false,
  'overwrite.cli.url' => 'https://nextcloud.{{server_domain}}/',
  'datadirectory' => '{{nextcloud_data_path}}',
  'dbtype' => 'mysql',
  'version' => '{{current_nextcloud_version}}',
  'dbname' => 'nextcloud',
  'dbhost' => 'mysql',
  'dbtableprefix' => 'oc_',
  'dbuser' => '{{vault_nextcloud_mysql_username}}',
  'dbpassword' => '{{vault_nextcloud_mysql_password}}',
  'installed' => true,
  'forcessl' => true,
  'syslog_tag' => 'nextcloud',
  'log_type' => 'file',
  'logfile' => '{{global_log}}nextcloud/nextcloud.log',
  'loglevel' => 2,
  'maintenance' => false,
  'mail_smtpmode' => 'smtp',
  'mail_smtphost' => 'postfix',
  'mail_domain' => '{{server_domain}}',
  'mail_from_address' => 'root',
  'default_phone_region' => '{{country}}',
  'appcodechecker' => false,
  'secret' => '{{vault_nextcloud_secret}}',
  'trashbin_retention_obligation' => 'auto',
  'updatechecker' => false,
  'appstore.experimental.enabled' => true,
  'enabledPreviewProviders' => array (
    'OC\Preview\Movie',
    'OC\Preview\Image',
#    'OC\Preview\Office',
    'OC\Preview\TXT',
    'OC\Preview\SVG',
    'OC\Preview\Bitmap',
#    'OC\Preview\Bundled',
  ),
#  'enabledPreviewProviders' => array (
#    0 => 'OC\\Preview\\PNG',
#    1 => 'OC\\Preview\\JPEG',
#    2 => 'OC\\Preview\\GIF',
#    3 => 'OC\\Preview\\BMP',
#    4 => 'OC\\Preview\\XBitmap',
#    5 => 'OC\\Preview\\MP3',
#    6 => 'OC\\Preview\\TXT',
#    7 => 'OC\\Preview\\MarkDown',
#    8 => 'OC\\Preview\\PDF',
#  ),
  'filesystem_check_changes' => 1,
  'memcache.local' => '\\OC\\Memcache\\APCu',
  'filelocking.enabled' => true,
  'memcache.locking' => '\\OC\\Memcache\\Redis',
  'redis' => 
  array (
    'host' => 'redis',
    'port' => 6379,
    'timeout' => 0,
    'dbindex' => 0,
  ),
  'mysql.utf8mb4' => true,
  'mail_smtpauthtype' => 'LOGIN',
  'theme' => 'smartserver'
);
