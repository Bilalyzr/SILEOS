const{chromium}=require('../../.toolchains/lab-qa/node_modules/playwright');
const fs=require('fs'),path=require('path');
(async()=>{
 const out=path.resolve(__dirname,'../../output/video/SILeos/product-captures');
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
 const shots=[];
 for(const[name,slug]of[['dna-interaction','cbse-dna-helix-3d'],['molecule-interaction','cbse-molecule-viewer-3d']]){
  const ctx=await browser.newContext({viewport:{width:1600,height:1080},recordVideo:{dir:out,size:{width:1600,height:1080}}});
  const begin=Date.now(),page=await ctx.newPage();
  await page.goto('http://127.0.0.1:3002/labs/'+slug,{waitUntil:'networkidle'});
  await page.evaluate(()=>window.scrollTo(0,260));
  const frame=page.frames().find(f=>f.url().includes('/labs/cbse/labs/'));
  await frame.locator('#cv').waitFor();await page.waitForTimeout(1000);
  const start=(Date.now()-begin)/1000;
  await page.waitForTimeout(1300);
  if(name==='dna-interaction'){
   await frame.locator('#unzip').focus();
   for(let i=0;i<30;i++){await page.keyboard.press('ArrowRight');await page.waitForTimeout(55);}
   await page.waitForTimeout(1000);
   await page.screenshot({path:path.join(out,'dna-unzipped.png')});
   for(let i=0;i<22;i++){await page.keyboard.press('ArrowLeft');await page.waitForTimeout(45);}
  }else{
   await frame.getByRole('button',{name:'CH₄',exact:true}).click();await page.waitForTimeout(1600);
   await page.screenshot({path:path.join(out,'molecule-methane.png')});
   await frame.getByRole('button',{name:'C₂H₆O',exact:true}).click();await page.waitForTimeout(1000);
   const box=await frame.locator('#cv').boundingBox();
   await page.mouse.move(box.x+box.width*.45,box.y+box.height*.45);await page.mouse.down();
   for(let i=0;i<35;i++){await page.mouse.move(box.x+box.width*(.45+i*.005),box.y+box.height*(.45+i*.002));await page.waitForTimeout(40);}
   await page.mouse.up();await page.waitForTimeout(800);
   await page.screenshot({path:path.join(out,'molecule-ethanol.png')});
  }
  await page.waitForTimeout(1500);const end=(Date.now()-begin)/1000;
  await page.locator('iframe').screenshot({path:path.join(out,name+'-panel.png')});
  const video=page.video();await ctx.close();const raw=await video.path();
  const renamed=path.join(out,name+'-raw.webm');fs.renameSync(raw,renamed);
  shots.push({name,start,end,duration:end-start,raw:path.basename(renamed),url:'http://127.0.0.1:3002/labs/'+slug});
 }
 await browser.close();fs.writeFileSync(path.join(out,'recording-timings.json'),JSON.stringify(shots,null,2));console.log(JSON.stringify(shots));
})().catch(e=>{console.error(e);process.exit(1)});
