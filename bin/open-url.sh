#!/bin/bash
grep -h -s --color=never '^URL=' "$@" | cut -d'=' -f2- | xargs firefox &