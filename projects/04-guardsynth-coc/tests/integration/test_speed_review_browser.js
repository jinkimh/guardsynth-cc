/* Real Chromium workflow checks in disposable contexts. Never upload synthetic responses. */
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');
const {chromium} = require(process.argv[2]);
const url = process.argv[3], output = process.argv[4], executablePath = process.argv[5];
(async()=>{
 await fs.mkdir(output,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath});
 try {
  const context=await browser.newContext({acceptDownloads:true,viewport:{width:1280,height:1000}});
  const page=await context.newPage(),errors=[],requests=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r.url()));
  await page.goto(url,{waitUntil:'load'});
  await page.waitForFunction(()=>document.getElementById('progress').textContent==='작성 완료 0/19');
  assert(await page.locator('#frame').evaluate(i=>i.complete&&i.naturalWidth>0));
  assert.equal(await page.locator('a[href]').count(),0);
  const packet=await page.locator('#packet').textContent();
  for(const forbidden of ['original_coc','raw_answer','zone_polygon','target_point','scene_clause_verdicts','cnl_file','rule_ref'])assert(!packet.includes('"'+forbidden+'"'));
  await page.screenshot({path:path.join(output,'initial.png'),fullPage:true});
  await page.locator('#save_scene').click();
  assert((await page.locator('#message').innerText()).includes('장면 1 임시 저장 완료'));
  await page.locator('#complete_scene').click();
  assert((await page.locator('#message').innerText()).includes('장면 1: 행동 4개 미응답, 판단 근거 필요'));
  assert((await page.locator('#scene').innerText()).startsWith('장면 1/19'));
  await page.locator('#final_save').click();
  assert((await page.locator('#message').innerText()).includes('장면 1: 행동 4개 미응답, 판단 근거 필요'));
  assert((await page.locator('#message').innerText()).includes('장면 19:'));
  for(const select of await page.locator('#actions select').all())await select.selectOption('UNDETERMINED');
  await page.locator('#reason').fill('BROWSER TEST ONLY — NOT A REVIEWER RESPONSE');
  await page.locator('#zoom').click();assert(await page.locator('#zoom_dialog').isVisible());
  assert(await page.locator('#zoom_image').evaluate(i=>i.complete&&i.naturalWidth>0));
  await page.screenshot({path:path.join(output,'zoom.png')});
  await page.locator('#close_zoom').click();
  assert.equal(await page.locator('#reason').inputValue(),'BROWSER TEST ONLY — NOT A REVIEWER RESPONSE');
  assert.equal(await page.locator('#actions select').first().inputValue(),'UNDETERMINED');
  await page.locator('#complete_scene').click();
  assert((await page.locator('#scene').innerText()).startsWith('장면 2/19'));
  assert((await page.locator('#message').innerText()).includes('장면 1 작성·브라우저 저장 완료'));
  await page.locator('#previous').click();
  assert((await page.locator('#scene_status').innerText()).includes('작성 완료'));
  await page.locator('#reason').fill('');
  await page.locator('#complete_scene').click();
  assert((await page.locator('#scene').innerText()).startsWith('장면 1/19'));
  assert((await page.locator('#message').innerText()).includes('판단 근거 필요'));
  await page.locator('#reason').fill('BROWSER TEST ONLY — NOT A REVIEWER RESPONSE');
  assert.equal(await page.locator('#reason').inputValue(),'BROWSER TEST ONLY — NOT A REVIEWER RESPONSE');
  await page.reload();assert.equal(await page.locator('#progress').innerText(),'작성 완료 1/19');
  const partialEvent=page.waitForEvent('download');await page.locator('#save').click();
  const partial=await partialEvent, partialPath=path.join(output,'test_partial.json');await partial.saveAs(partialPath);
  const draft=JSON.parse(await fs.readFile(partialPath,'utf8'));assert.equal(draft.status,'DRAFT_NOT_SUBMITTED');
  await page.evaluate(()=>localStorage.clear());await page.reload();
  assert.equal(await page.locator('#progress').innerText(),'작성 완료 0/19');
  await page.locator('#restore').setInputFiles(partialPath);
  await page.waitForFunction(()=>document.getElementById('message').textContent==='JSON 복원 완료');
  assert.equal(await page.locator('#progress').innerText(),'작성 완료 1/19');
  const badPath=path.join(output,'test_invalid.json');await fs.writeFile(badPath,JSON.stringify({...draft,packet_sha256:'wrong'}));
  await page.locator('#restore').setInputFiles(badPath);
  await page.waitForFunction(()=>document.getElementById('message').textContent.startsWith('복원 거부:'));
  assert.equal(await page.locator('#progress').innerText(),'작성 완료 1/19');
  for(let i=0;i<19;i++){
   for(const select of await page.locator('#actions select').all())await select.selectOption('UNDETERMINED');
   await page.locator('#reason').fill('BROWSER TEST ONLY — NOT A REVIEWER RESPONSE');
   if(i<18)await page.locator('#next').click();
  }
  assert.equal(await page.locator('#progress').innerText(),'작성 완료 19/19');
  await page.locator('#complete_scene').click();
  assert((await page.locator('#scene').innerText()).startsWith('장면 19/19'));
  assert((await page.locator('#message').innerText()).includes('모든 장면 작성 완료'));
  const finalEvent=page.waitForEvent('download');await page.locator('#final_save').click();
  const finalDownload=await finalEvent, finalPath=path.join(output,'test_completed.json');await finalDownload.saveAs(finalPath);
  const final=JSON.parse(await fs.readFile(finalPath,'utf8'));
  assert.equal(final.reviewer_id,'Jonh');assert.equal(final.status,'COMPLETED_NOT_RECEIVED');
  assert.equal(final.records.length,19);assert(final.exported_at);
  assert(final.records.every(r=>Object.values(r.action_assessments).every(a=>a==='UNDETERMINED')));
  await context.close();
  const fresh=await browser.newContext();const clean=await fresh.newPage();await clean.goto(url);
  assert.equal(await clean.locator('#progress').innerText(),'작성 완료 0/19');await fresh.close();
  assert.deepEqual(errors,[]);
  assert(requests.every(r=>r===url||r.startsWith('data:')||r.startsWith('blob:')));
  await fs.writeFile(path.join(output,'browser_checks.json'),JSON.stringify({status:'PASS',url,
   browser_version:browser.version(),initial_count:'0/19',image_decoded:true,zoom_return_preserves_answers:true,
   scene_navigation_preserves_answers:true,reload_preserves_answers:true,partial_export_restore:true,
   per_scene_save_complete:true,incomplete_scene_blocks_advance:true,last_scene_completion:true,
   invalid_restore_rejected:true,missing_guidance:true,final_json_19_records:true,fresh_context_count:'0/19',
   no_source_links:true,no_unexpected_requests:true,console_errors:errors,
   test_only:true,real_responses_received:0,operational_submission_directory_written:false},null,2)+'\n');
  console.log('PASS: real Chromium workflow; disposable test responses only');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
