#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "=========================================================="
echo "🛠️  Running Full Project Setup for macOS"
echo "=========================================================="

# 1. Ensure Node.js is installed
if ! command -v node >/dev/null 2>&1; then
    if [ -x "$HOME/.local/node/bin/node" ]; then
        export PATH="$HOME/.local/node/bin:$PATH"
    else
        echo "Installing Node.js v20.20.2 (LTS) into ~/.local/node..."
        mkdir -p "$HOME/.local"
        curl -fsSL https://nodejs.org/dist/v20.20.2/node-v20.20.2-darwin-arm64.tar.gz | tar -xz -C "$HOME/.local"
        rm -rf "$HOME/.local/node"
        mv "$HOME/.local/node-v20.20.2-darwin-arm64" "$HOME/.local/node"
        export PATH="$HOME/.local/node/bin:$PATH"
        
        # Add to ~/.zshrc if not present
        if ! grep -q ".local/node/bin" "$HOME/.zshrc" 2>/dev/null; then
            echo 'export PATH="$HOME/.local/node/bin:$PATH"' >> "$HOME/.zshrc"
        fi
    fi
fi

echo "✅ Node.js: $(node -v) | npm: $(npm -v)"

# 2. Setup Python virtual environment
echo "Setting up Python virtual environment in backend/venv..."
if [ ! -d "$ROOT_DIR/backend/venv" ]; then
    python3 -m venv "$ROOT_DIR/backend/venv"
fi

"$ROOT_DIR/backend/venv/bin/pip" install --upgrade pip
"$ROOT_DIR/backend/venv/bin/pip" install -r "$ROOT_DIR/backend/requirements.txt"
echo "✅ Python backend dependencies installed."

# 3. Setup Frontend dependencies & binaries
echo "Setting up Frontend dependencies in frontend/..."
cd "$ROOT_DIR/frontend"
npm install
chmod +x node_modules/.bin/* 2>/dev/null || true
cd "$ROOT_DIR"
echo "✅ Frontend dependencies installed & binaries configured."

# 4. Environment files
if [ ! -f "$ROOT_DIR/.env" ] && [ -f "$ROOT_DIR/backend/.env" ]; then
    cp "$ROOT_DIR/backend/.env" "$ROOT_DIR/.env"
fi

if [ ! -f "$ROOT_DIR/frontend/.env.local" ]; then
    echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api" > "$ROOT_DIR/frontend/.env.local"
fi

echo "=========================================================="
echo "🎉 Setup complete! You can now start the application with:"
echo "   ./start.sh"
echo "=========================================================="
