HOME_NET = 'any'
EXTERNAL_NET = 'any'

ips =
{
  mode = tap,
  rules =
  [[
    include /usr/local/etc/snort/rules/local.rules
  ]]
}

alert_fast =
{
  file = true,
  packet = false,
  limit = 0
}