import sys
import os
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def check_links(input_file, output_report_file):
    # Absolute path for the local file
    file_path = f"file://{os.path.abspath(input_file)}"
    results = []

    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(headless=True, channel='chromium')
        c = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36")
        page = await c.new_page()

        print(f"Reading file: {input_file}...")
        try:
            await page.goto(file_path)
        except Exception as e:
            print(f"Error loading the local file: {e}")
            await browser.close()
            return

        # Locate all cells with class "url"
        url_cells = await page.locator(".url").all()
        urls = [await cell.inner_text() for cell in url_cells]
        
        print(f"Found {len(urls)} URLs to check.")

        # Iterate through each URL found
        for url in urls:
            url = url.strip()
            url = '' if url == 'URL' else url
            if not url:
                continue

            # strip leading and trailing apostrophes that exists in every url
            url = url[1:-1]
            print(f"Checking: {url}")
            try:
                # Attempt to navigate to the URL with a 10-second timeout
                response = await page.goto(url, timeout=10000, wait_until="load")
                if response and response.ok:
                    results.append({"url": url, "status": "Success", "details": f"Status {response.status}"})
                else:
                    status_code = response.status if response else "No Response"
                    results.append({"url": url, "status": "Error", "details": f"Failed with status {status_code}"})
            except Exception as e:
                results.append({"url": url, "status": "Error", "details": str(e)})
            print(results[-1]['details'])

        await browser.close()

    generate_report(results, output_report_file)

def generate_report(results, output_report_file):
    output_file = os.path.abspath(output_report_file)
    
    html_content = f"""
    <html>
    <head>
        <title>Link Check Results</title>
        <style>
            table {{ border-collapse: collapse; width: 100%; font-family: sans-serif; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            th {{ background-color: #f4f4f4; }}
            .success {{ color: green; font-weight: bold; }}
            .error {{ color: red; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h2>URL Verification Report</h2>
        <table>
            <tr>
                <th>URL</th>
                <th>Result</th>
                <th>Details</th>
            </tr>
    """

    total_success = 0
    total_fail = 0
    for row in results:
        status_class = "success" if row['status'] == "Success" else "error"
        if status_class == 'error':
            total_fail += 1
            html_content += f"""
                <tr>
                    <td><a href="{row['url']}">{row['url']}</a></td>
                    <td class="{status_class}">{row['status']}</td>
                    <td>{row['details']}</td>
                </tr>
            """
        else:
            total_success += 1

    html_content += f"</table><p>Total errors: {total_fail} </p></body></html>"

    with open(output_file, "w") as f:
        f.write(html_content)
    
    print(f"\nScan complete. Results saved to: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python link_checker.py <path_to_html_file> <outputreportname>")
    else:
        asyncio.run(check_links(sys.argv[1], sys.argv[2]))