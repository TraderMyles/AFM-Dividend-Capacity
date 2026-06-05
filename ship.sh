#!/bin/bash
echo "Commit message:"
read message
git add .
git commit -m "$message"
echo "Push to main? (y/n)"
read confirm
if [ "$confirm" = "y" ]; then
    git push origin main
    echo "Pushed."
else
    echo "Aborted."
fi