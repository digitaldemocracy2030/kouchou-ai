echo "Kouchou-AI Setup Tool"
echo "====================="

if ! docker info > /dev/null 2>&1; then
  echo "Docker is not running."
  echo "Please start Docker and try again."
  read -p "Press Enter to exit..."
  exit 1
fi

read -p "Enter your OpenAI API key (optional): " OPENAI_API_KEY
read -p "Enter your Gemini API key (optional): " GEMINI_API_KEY

cat > .env << EOL
OPENAI_API_KEY=${OPENAI_API_KEY}
GEMINI_API_KEY=${GEMINI_API_KEY}
PUBLIC_API_KEY=public
ADMIN_API_KEY=admin
ENVIRONMENT=development
STORAGE_TYPE=local
NEXT_PUBLIC_PUBLIC_API_KEY=public
NEXT_PUBLIC_ADMIN_API_KEY=admin
NEXT_PUBLIC_CLIENT_BASEPATH=http://localhost:3000
NEXT_PUBLIC_API_BASEPATH=http://localhost:8000
API_BASEPATH=http://api:8000
NEXT_PUBLIC_SITE_URL=http://localhost:3000
EOL

echo "Starting Docker environment..."
docker compose up -d --build

echo ""
echo "Setup completed!"
echo "You can now access the following URLs in your browser:"
echo "  http://localhost:3000 - Report Viewer"
echo "  http://localhost:4000 - Admin Panel"
echo ""
read -p "Press Enter to continue..."
