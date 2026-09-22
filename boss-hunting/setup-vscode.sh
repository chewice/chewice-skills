#!/usr/bin/env bash
set -euo pipefail

mkdir -p .vscode

cat > .vscode/settings.json <<'EOF'
{
    "r.rpath.linux": "${workspaceFolder}/.pixi/envs/default/bin/R",
    "r.rterm.linux": "${workspaceFolder}/.pixi/envs/default/bin/R"
}
EOF
