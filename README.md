#### Update - This project is on hold until I create an App within the Meta Developers Portal. Will look at this again in a week or two (est. November 1, 2024).

# Threads Auto-Poster

This project allows you to schedule and automatically post content to Threads using the Threads API. It uses GitHub Pages for the user interface and GitHub Actions for scheduling and posting.

## Setup

1. Clone the two new GitHub repositories:
   - `threads-auto-poster` (This repository)
   - `threads-media-storage` (For storing media files that you upload from your machine)

2. Clone the `threads-auto-poster` repository to your local machine.

3. Update the following files with your GitHub username:
   - `docs/script.js`: Replace `YOUR_USERNAME` with your GitHub username

4. In your GitHub repository settings:
   - Enable GitHub Pages and set the source to the `docs/` folder on the main branch.
   - Add the following secrets:
     - `THREADS_ACCESS_TOKEN`: Your Threads API access token
     - `THREADS_USER_ID`: Your Threads user ID
     - `GITHUB_TOKEN`: A personal access token with repo scope

5. Commit and push all changes to GitHub.

## Usage

1. Access the web interface through the GitHub Pages URL (typically `https://your-username.github.io/threads-auto-poster/`).

2. To add a new post to the queue:
   - Enter the post text
   - Select the media type (Text, Image, or Video)
   - If Image or Video is selected, choose the file to upload
   - Set the scheduled time for the post
   - Click "Add to Queue"

3. The system will automatically:
   - Upload any media to the `threads-media-storage` repository
   - Add the post to the queue
   - Schedule the post for publishing

4. The GitHub Action, `post-to-threads.yml`, will run every hour, check the queue, and post to Threads if there's a scheduled post due.

## Files and Their Purposes

- `docs/index.html`: The web interface for adding posts to the queue
- `docs/script.js`: Handles the logic for the web interface and interacts with the GitHub API
- `src/post_to_threads.py`: Publishes posts to Threads
- `src/queue_manager.py`: Manages the posting queue
- `.github/workflows/post-to-threads.yml`: GitHub Action for posting to Threads
- `.github/workflows/update-queue.yml`: GitHub Action for updating and sorting the queue
- `queue.json`: Stores the queue of posts to be published

## Troubleshooting

- If posts aren't being published, check the GitHub Actions logs for any error messages.
- Ensure that your Threads API key and user ID are correctly set in the repository secrets.
- Verify that the personal access token has the necessary permissions to write to both repositories.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the [MIT License](LICENSE).

## Folder Structure

``` json
threads-auto-poster/
├── .github/
│   └── workflows/
│       ├── post-to-threads.yml
│       └── update-queue.yml
├── docs/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── src/
│   ├── post_to_threads.py
│   └── queue_manager.py
├── .gitignore
├── README.md
├── requirements.txt
└── queue.json

threads-media-storage/
└── (This repository will be populated with media files as they are uploaded)
```
