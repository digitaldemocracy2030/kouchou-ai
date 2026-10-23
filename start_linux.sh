echo "Starting Kouchou-AI..."

if ! docker info > /dev/null 2>&1; then
  echo "Docker is not running."
  echo "Please start Docker and try again."
  read -p "Press Enter to exit..."
  exit 1
fi

if ! docker compose up -d; then
  echo "" >&2
  echo "Failed to start Kouchou-AI." >&2
  echo "Please check the error messages above and try again." >&2
  read -p "Press Enter to exit..."
  exit 1
fi

echo ""
echo "Kouchou-AI is now running!"
echo "You can access the following URLs in your browser:"
echo "  http://localhost:3000 - Report Viewer"
echo "  http://localhost:4000 - Admin Panel"
echo ""
