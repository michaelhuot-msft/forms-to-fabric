#!/bin/sh
# Install Git hooks for the Forms to Fabric project
# Run once after cloning: sh scripts/install-hooks.sh

HOOKS_DIR="$(git rev-parse --show-toplevel)/.git/hooks"
SRC_DIR="$(git rev-parse --show-toplevel)/hooks"

if [ -f "$SRC_DIR/pre-commit" ]; then
    cp "$SRC_DIR/pre-commit" "$HOOKS_DIR/pre-commit"
    chmod +x "$HOOKS_DIR/pre-commit"
    echo "✅ Pre-commit hook installed"
else
    echo "❌ hooks/pre-commit not found"
    exit 1
fi

echo ""
echo "Hooks installed. Bicep templates will be validated before each commit."
