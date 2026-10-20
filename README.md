# Aviation Career Radar · 0.2.0

This is the next working revision of John's personal aviation opportunity dashboard. The Windows application runs locally, opens in your browser, and stores your data separately from the application. No paid AI service or account is required to run it.

**Start with [START-HERE-GITHUB.md](START-HERE-GITHUB.md)** to build the Windows application using the same GitHub Actions process you already tested. This source ZIP is not the Windows application artifact.

## What's included

- CFI, other early-career flying, regional airline, longer-term jet careers, and pathways/recruiting sections. Ohio + surrounding states is the default for CFI/early roles; the others default nationwide. Filters never use qualifications to hide jobs.
- Separate **My Opportunities** tab for pinned listings, notes, dated interactions, optional follow-up dates, and next steps. Read status, interest, application progress and availability are independent. Closed/uninteresting records remain stored.
- Expand a listing for work location, published pay, requirements and a shared employer notebook. Headquarters, operating footprint, pilot bases, residence/commuting and transfers are separate fields.
- Requirement colors compare an approved profile with supported facts. Green = appears met, red = appears unmet, gray = unknown/ambiguous. Overall green also requires reviewing the completeness of the requirements. Planned ratings never count as earned.
- **Profile & imports:** take the included prompt and your résumé to ChatGPT, import its JSON file, inspect the preview, then approve. Previous profiles can be restored. A separate résumé archive does not silently change qualifications.
- Add opportunities or word-of-mouth leads without a URL, add sources to each section, and link/merge an official listing later while retaining history.
- **Sources & testing:** editable individual connections, public-page link rules, bounded pagination, optional detail requests, expected sample checks, previews, recent test history and a focused troubleshooting export.
- **Market briefings:** save a dated snapshot, export/copy the prompt to ChatGPT online, then paste/import its answer. The imported answer remains separate commentary.

## Coverage limits

This is a source monitor and organizing tool, not a guarantee of all available jobs. Public static HTML/JobPosting metadata and public Lever/Greenhouse feeds are supported. JavaScript-only sites, login-only systems, restricted pages and different API formats need individual source work or manual bookmarks. Adding a URL cannot make every site automatically compatible. A successful page download is explicitly distinguished from extracted listings. Nothing bypasses website access restrictions.

Seed sources, employer notes and program relationships retain their original dated research. They are starting points, not newly verified vacancies or a claim that every KSU program is included. Public announcements are watched for changes; refreshes do not automatically rewrite factual employer/program notes. No automatic source discovery, email access, AI API, browser submission or ChatGPT response capture is included.

The app refreshes when you click **Refresh sources**; source tests run only while the application is open. It reminds you when a new weekly briefing snapshot is due on the overview; it does not schedule or send emails.

## Data and development

Windows data: `%LOCALAPPDATA%\AviationCareerRadar`. Keep this folder private and separate from your GitHub source. The first upgrade automatically backs up the previous SQLite database before migrating it. Download a full backup from the old app before upgrading.

See [RELEASE-NOTES.md](RELEASE-NOTES.md), [DEVELOPMENT.md](DEVELOPMENT.md) and [BUILD-VERIFICATION.md](BUILD-VERIFICATION.md). Source research remains in [RESEARCH.md](RESEARCH.md).
