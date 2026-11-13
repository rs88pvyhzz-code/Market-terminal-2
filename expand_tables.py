"""Open every "Show all" table so tests can reach rows beyond the first twenty."""
def expand(page):
    page.evaluate("document.querySelectorAll('.polish-more').forEach(b=>{if(/^Show all/.test(b.textContent))b.click();})")
    page.wait_for_timeout(80)
