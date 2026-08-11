Name:		grommunio-dav
Version:	1.7
Release:	1
Source0:	https://github.com/grommunio/grommunio-dav/releases/download/%{version}/grommunio-dav-%{version}.tar.zst
# Composer production deps (sabre/dav, monolog, psr/log); no network at build time
Source1:	grommunio-dav-%{version}-vendor.tar.zst
Summary:	CalDAV and CardDAV interface for grommunio
URL:		https://github.com/grommunio/grommunio-dav
License:	AGPL-3.0 AND BSD-3-Clause AND MIT
Group:		Servers
BuildArch:	noarch

Requires:	php
Requires:	php-fpm
Requires:	php-gromox
Requires:	php-ctype
Requires:	php-curl
Requires:	php-dom
Requires:	php-iconv
Requires:	php-mbstring
Requires:	php-pdo
Requires:	php-pdo_sqlite
Requires:	php-sqlite3
Requires:	php-xmlreader
Requires:	php-xmlwriter
Requires:	grommunio-mapi-header-php
Requires:	gromox
Requires:	nginx

%description
grommunio-dav provides CalDAV and CardDAV for clients such as Apple
Calendar/Contacts, Thunderbird and other DAV-capable applications.
It talks to Gromox via the PHP MAPI bindings.

The company Global Address List can be published as a read-only
CardDAV address book (GAL_ENABLED in the config).

This package ships a dedicated php-fpm instance (php-fpm@grommunio-dav)
and an nginx snippet in /etc/nginx/grommunio.d/. Enable the instance
and reload nginx after install.

%prep
%autosetup -p1 -a1

%install
mkdir -p %{buildroot}%{_datadir}/%{name}
cp -a lib vendor server.php LICENSE README.rst %{buildroot}%{_datadir}/%{name}/
# Drop composer/dev leftovers from vendored libs
rm -rf %{buildroot}%{_datadir}/%{name}/vendor/bin \
	%{buildroot}%{_datadir}/%{name}/vendor/*/.github \
	%{buildroot}%{_datadir}/%{name}/vendor/*/*/.github
find %{buildroot}%{_datadir}/%{name}/vendor -type d -name bin -exec rm -rf {} +
find %{buildroot}%{_datadir}/%{name}/vendor \( -name '.php_cs*' -o -name '.php-cs-fixer*' -o -name '.travis.yml' -o -name '.empty' \) -delete
cat >%{buildroot}%{_datadir}/%{name}/version.php <<EOF
<?php
if (!defined("GDAV_VERSION")) {
	define("GDAV_VERSION", "%{version}");
}
EOF

mkdir -p %{buildroot}%{_sysconfdir}/%{name}
sed -e "s|define('MAPI_SERVER', 'default:');|define('MAPI_SERVER', 'unix:/run/gromox/zcore.sock');|" \
    -e "s|define('DEVELOPER_MODE', true);|define('DEVELOPER_MODE', false);|" \
	config.php >%{buildroot}%{_sysconfdir}/%{name}/config.php
sed -e 's/level = TRACE/level = INFO/' glogger.ini \
	>%{buildroot}%{_sysconfdir}/%{name}/glogger.ini
ln -s %{_sysconfdir}/%{name}/config.php %{buildroot}%{_datadir}/%{name}/config.php
ln -s %{_sysconfdir}/%{name}/glogger.ini %{buildroot}%{_datadir}/%{name}/glogger.ini

install -d -m 0770 %{buildroot}%{_localstatedir}/lib/%{name}
install -d -m 0770 %{buildroot}%{_localstatedir}/log/%{name}

install -d %{buildroot}%{_sysconfdir}/logrotate.d
cat >%{buildroot}%{_sysconfdir}/logrotate.d/%{name} <<EOF
%{_localstatedir}/log/%{name}/*.log {
	missingok
	notifempty
	sharedscripts
	su www www
}
EOF

install -d %{buildroot}%{_sysconfdir}/php-fpm-instances.d
cat >%{buildroot}%{_sysconfdir}/php-fpm-instances.d/grommunio-dav.conf <<'EOF'
[global]
error_log=syslog

[grommunio-dav]
user=www
group=www
listen=/run/php-fpm/grommunio-dav.sock
listen.owner=www
listen.group=www
listen.mode=0660

php_admin_value[error_log]=/var/log/grommunio-dav/php-fpm.log
php_admin_value[log_errors]=on
php_admin_value[memory_limit]=256M
php_admin_value[max_execution_time]=360

pm=dynamic
pm.max_children=50
pm.start_servers=1
pm.min_spare_servers=1
pm.max_spare_servers=12

env[GROMOX_CONFIG_DIR]=/etc/gromox
php_admin_value[open_basedir]=/usr/share/grommunio-dav:/etc/grommunio-dav:/var/lib/grommunio-dav:/var/log/grommunio-dav:/etc/gromox:/usr/share/php-mapi:/usr/share/php:/run/gromox
php_admin_value[opcache.enable]=0
php_admin_value[opcache.jit]=0
php_admin_value[mapi.zcore_socket]=/run/gromox/zcore.sock
EOF

cat >%{buildroot}%{_sysconfdir}/php-fpm-instances.d/grommunio-dav.env <<'EOF'
PHP_FPM_ARGS="-d extension=mapi.so -d opcache.enable=0 -d opcache.jit=0 -d opcache.enable_cli=0"
EOF

install -d %{buildroot}%{_sysconfdir}/nginx/grommunio.d
cat >%{buildroot}%{_sysconfdir}/nginx/grommunio.d/dav.conf <<'EOF'
location = /.well-known/caldav { return 301 /dav; }
location = /.well-known/carddav { return 301 /dav; }

location ^~ /dav {
	include fastcgi_params;
	fastcgi_pass unix:/run/php-fpm/grommunio-dav.sock;
	fastcgi_param SCRIPT_FILENAME /usr/share/grommunio-dav/server.php;
	fastcgi_param HTTP_PROXY "";
	fastcgi_read_timeout 360;
	fastcgi_param PHP_VALUE "memory_limit=256M
max_execution_time=360";
}
EOF

%files
%{_datadir}/%{name}
%dir %{_sysconfdir}/%{name}
%config(noreplace) %{_sysconfdir}/%{name}/config.php
%config(noreplace) %{_sysconfdir}/%{name}/glogger.ini
%config(noreplace) %{_sysconfdir}/logrotate.d/%{name}
%config(noreplace) %{_sysconfdir}/php-fpm-instances.d/grommunio-dav.conf
%config(noreplace) %{_sysconfdir}/php-fpm-instances.d/grommunio-dav.env
%config(noreplace) %{_sysconfdir}/nginx/grommunio.d/dav.conf
%dir %attr(0770,www,www) %{_localstatedir}/lib/%{name}
%dir %attr(0770,www,www) %{_localstatedir}/log/%{name}
