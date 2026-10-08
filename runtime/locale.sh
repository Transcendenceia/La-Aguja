# shellcheck shell=bash
# Share the runtime's literal catalog. Never source/eval a data/config file.
aguja_refresh_locale() {
    local aguja_locale_value aguja_locale_helper
    aguja_locale_helper=/usr/lib/aguja/i18n.py
    [ -r "$aguja_locale_helper" ] || return 0
    aguja_locale_value=$(python3 "$aguja_locale_helper" --system-locale) || return 0
    [ -n "$aguja_locale_value" ] || return 0
    export LANG="$aguja_locale_value" LC_ALL="$aguja_locale_value"
}
aguja_refresh_locale
