const{chromium}=require('../../.toolchains/lab-qa/node_modules/playwright');
const fs=require('fs'),path=require('path');
(async()=>{
 const out=path.resolve(__dirname,'../../output/video/SILeos/product-captures');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 const ctx=await browser.newContext({viewport:{width:1600,height:1000},deviceScaleFactor:1});
 const page=await ctx.newPage();
 for(const[name,url]of[['lab-library','/labs'],['dna-workspace','/labs/cbse-dna-helix-3d'],['molecule-workspace','/labs/cbse-molecule-viewer-3d']]){
  await page.goto('http://127.0.0.1:3002'+url,{waitUntil:'networkidle'});
  await page.waitForTimeout(1200);
  await page.screenshot({path:path.join(out,name+'.png')});
  console.log(JSON.stringify({name,url,title:await page.title(),text:(await page.locator('body').innerText()).slice(0,1600),frames:page.frames().map(f=>f.url())}));
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
