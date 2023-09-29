const { chromium } = require('playwright');

(async () => {

  const url = process.argv[2];
  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    await page.goto(url);
    let title = await page.title();
    let body = await page.$eval('body', el => el.innerHTML);  //innerText
    title = title.replace(/"/g, "'");
    body = body.replace(/"/g, "'");
    const result = { title, body };
    console.log(JSON.stringify(result));
  } catch (e) {
    console.log(JSON.stringify({title: "ERROR", body: ""}));
  } finally {
    await browser.close();
  }
})();

