# Deployment & Automation Guide

## 1. Enable GitHub Pages

To view your dashboard online, you need to enable GitHub Pages:

1.  Go to your repository on GitHub.
2.  Click **Settings** (top right tab).
3.  On the left sidebar, click **Pages**.
4.  Under **Build and deployment** > **Source**, select **Deploy from a branch**.
5.  Under **Branch**, select **main** and folder **/(root)**.
6.  Click **Save**.

Your dashboard will be live at: `https://<your-username>.github.io/<repo-name>/report.html`

## 2. Automated Daily Updates

The project includes a GitHub Action (`.github/workflows/daily_scrape.yml`) that runs automatically:

*   **Schedule**: Monday to Friday at 6:00 PM (PH Time).
*   **Action**: Fetches new stock data and updates the `report.html`.

### How to Manually Trigger

1.  Go to the **Actions** tab in your repository.
2.  Click **Daily Stock Scrape** on the left.
3.  Click **Run workflow** -> **Run workflow**.
