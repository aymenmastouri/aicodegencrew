import { test, expect, Page } from '@playwright/test';

/**
 * Demo Showcase — Full walkthrough
 *
 * Flow:
 *   Splash  → branding
 *   Ch 1    → Dashboard tour (3 layers, 9 phases with tooltips)
 *   Ch 2    → Knowledge page (extract + document groups)
 *   Ch 3    → Reports: arc42 docs with scroll + C4
 *   Ch 4    → Inputs + Settings + Run Pipeline (preset, parallel, select 2 tasks, run)
 *   Ch 5    → Triage results deep dive
 *   Ch 6    → Development plans deep dive
 *   Finale  → Stats + dashboard beauty shot
 *
 * Run:   npx playwright test --project=demo e2e/demo-showcase.spec.ts
 * Video: test-results/demo-showcase-Demo-Showcase-.../video.webm
 */

const API = 'http://localhost:4200/api';

// ── Timing ──
const P      = 800;   // short pause
const LP     = 1500;  // long pause
const RP     = 2500;  // read pause
const DR     = 3500;  // deep read
const FP     = 500;   // fast

// ═══════════════════════════════════════════════════════════════
//  HELPERS
// ═══════════════════════════════════════════════════════════════

async function p(page: Page, ms = P) {
  await page.waitForTimeout(ms);
}

async function scrollDown(page: Page, px: number, ms = 1500) {
  await page.evaluate(({ px, ms }) => {
    const c = document.querySelector('mat-sidenav-content') as HTMLElement;
    if (!c) return;
    const s = c.scrollTop;
    const t0 = performance.now();
    (function f() {
      const e = Math.min((performance.now() - t0) / ms, 1);
      c.scrollTop = s + px * (0.5 - Math.cos(e * Math.PI) / 2);
      if (e < 1) requestAnimationFrame(f);
    })();
  }, { px, ms });
  await p(page, ms + 200);
}

async function scrollTop(page: Page) {
  await page.evaluate(() => {
    const c = document.querySelector('mat-sidenav-content');
    if (c) c.scrollTop = 0;
  });
  await p(page, FP);
}

async function scrollEl(page: Page, sel: string) {
  const el = page.locator(sel).first();
  if (await el.isVisible({ timeout: 2000 }).catch(() => false)) {
    await el.evaluate(e => e.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    await p(page, FP);
  }
}

async function scrollH4(page: Page, text: string) {
  const h = page.locator(`h4:has-text("${text}")`).first();
  if (await h.isVisible({ timeout: 2000 }).catch(() => false)) {
    await h.evaluate(e => e.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    await p(page, FP);
  }
}

// ── Overlays ──

async function splash(page: Page) {
  await page.evaluate(() => {
    const d = document.createElement('div');
    d.id = 'ds';
    Object.assign(d.style, {
      position:'fixed',inset:'0',zIndex:'100000',
      background:'linear-gradient(135deg,#001B3D,#002B5C)',
      display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',
      fontFamily:'system-ui,sans-serif',color:'#fff',transition:'opacity .8s',
    });
    d.innerHTML = `
      <div style="font-size:52px;font-weight:700;letter-spacing:-1px;margin-bottom:16px">
        <span style="color:#12abdb">SDLC</span> Pilot
      </div>
      <div style="font-size:22px;color:rgba(255,255,255,.6)">
        AI-Powered Development Lifecycle Automation
      </div>
      <div style="display:flex;align-items:center;gap:10px;margin-top:24px">
        <span style="font-size:11px;color:rgba(255,255,255,.3);letter-spacing:1.5px;text-transform:uppercase">by</span>
        
        <span style="width:1px;height:16px;background:rgba(255,255,255,.15);margin:0 8px"></span>
        <span style="font-size:14px;font-style:italic;color:rgba(255,255,255,.4);letter-spacing:.5px">Make it real</span>
      </div>
      <div style="margin-top:24px;font-size:15px;color:rgba(255,255,255,.35);max-width:520px;text-align:center;line-height:1.6">
        100% on-premises — your source code and tickets never leave the company network
      </div>
      <div style="margin-top:40px;font-size:12px;color:rgba(255,255,255,.2);letter-spacing:2px;text-transform:uppercase">
        Live Demo
      </div>`;
    document.body.appendChild(d);
  });
  await p(page, 3000);
  await page.evaluate(() => {
    const d = document.getElementById('ds');
    if (d) { d.style.opacity = '0'; setTimeout(() => d.remove(), 800); }
  });
  await p(page, 1000);
}

async function chapter(page: Page, n: number, title: string, sub: string) {
  await page.evaluate(({ n, t, s }) => {
    document.getElementById('sub')?.remove();
    document.getElementById('ch')?.remove();
    const d = document.createElement('div');
    d.id = 'ch';
    Object.assign(d.style, {
      position:'fixed',inset:'0',zIndex:'100000',
      background:'linear-gradient(135deg,#001B3D,#002B5C)',
      display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',
      fontFamily:'system-ui,sans-serif',color:'#fff',transition:'opacity .6s',
    });
    d.innerHTML = `
      <div style="font-size:14px;font-weight:600;letter-spacing:3px;text-transform:uppercase;color:#12abdb;margin-bottom:12px">Chapter ${n}</div>
      <div style="font-size:38px;font-weight:600;margin-bottom:12px">${t}</div>
      <div style="font-size:18px;color:rgba(255,255,255,.5)">${s}</div>`;
    document.body.appendChild(d);
  }, { n, t: title, s: sub });
  await p(page, 2500);
  await page.evaluate(() => {
    const d = document.getElementById('ch');
    if (d) { d.style.opacity = '0'; setTimeout(() => d.remove(), 600); }
  });
  await p(page, 800);
}

async function sub(page: Page, text: string, ms = RP) {
  await page.evaluate(t => {
    document.getElementById('sub')?.remove();
    const d = document.createElement('div');
    d.id = 'sub';
    Object.assign(d.style, {
      position:'fixed',top:'80px',left:'50%',transform:'translateX(-50%)',
      background:'rgba(0,27,61,.92)',color:'#fff',
      padding:'16px 36px',borderRadius:'14px',
      fontSize:'19px',fontWeight:'500',fontFamily:'system-ui,sans-serif',
      zIndex:'99999',pointerEvents:'none',
      maxWidth:'80%',textAlign:'center',boxShadow:'0 6px 32px rgba(0,0,0,.4)',
      borderBottom:'2px solid #12abdb',
      backdropFilter:'blur(8px)',
    });
    d.textContent = t;
    document.body.appendChild(d);
  }, text);
  await p(page, ms);
}

async function hideSub(page: Page) {
  await page.evaluate(() => document.getElementById('sub')?.remove());
}

async function phaseTip(page: Page, name: string, text: string, ms = RP) {
  await page.evaluate(({ name, text }) => {
    document.getElementById('pt')?.remove();
    const card = Array.from(document.querySelectorAll('.phase-card')).find(c =>
      c.querySelector('.phase-name')?.textContent?.trim().toLowerCase().includes(name.toLowerCase()));
    if (!card) return;
    (card as HTMLElement).style.outline = '2px solid #12abdb';
    (card as HTMLElement).style.outlineOffset = '3px';
    card.setAttribute('data-hl', '1');

    const r = card.getBoundingClientRect();
    const tip = document.createElement('div');
    tip.id = 'pt';
    tip.textContent = text;
    const right = window.innerWidth - r.right > 200;
    Object.assign(tip.style, {
      position:'fixed',background:'rgba(0,0,0,.88)',color:'#fff',
      padding:'10px 18px',borderRadius:'8px',fontSize:'16px',
      fontFamily:'system-ui,sans-serif',fontWeight:'500',
      zIndex:'99999',maxWidth:'360px',lineHeight:'1.4',
      boxShadow:'0 4px 20px rgba(0,0,0,.3)',pointerEvents:'none',
    });
    if (right) { tip.style.top = `${r.top + r.height/2 - 20}px`; tip.style.left = `${r.right + 12}px`; }
    else { tip.style.top = `${r.bottom + 8}px`; tip.style.left = `${r.left}px`; }
    document.body.appendChild(tip);
  }, { name, text });
  await p(page, ms);
  await page.evaluate(() => {
    document.getElementById('pt')?.remove();
    document.querySelectorAll('[data-hl]').forEach(c => {
      (c as HTMLElement).style.outline = '';
      (c as HTMLElement).style.outlineOffset = '';
      c.removeAttribute('data-hl');
    });
  });
}

async function layerBadge(page: Page, label: string, color: string, ms = LP) {
  await page.evaluate(({ l, c }) => {
    document.getElementById('lb')?.remove();
    const d = document.createElement('div');
    d.id = 'lb';
    d.textContent = l;
    Object.assign(d.style, {
      position:'fixed',top:'70px',left:'50%',transform:'translateX(-50%)',
      background:c,color:'#fff',padding:'6px 20px',borderRadius:'20px',
      fontSize:'13px',fontWeight:'700',letterSpacing:'2px',textTransform:'uppercase',
      zIndex:'99999',pointerEvents:'none',boxShadow:'0 2px 12px rgba(0,0,0,.2)',
    });
    document.body.appendChild(d);
  }, { l: label, c: color });
  await p(page, ms);
}

async function hideLayer(page: Page) {
  await page.evaluate(() => document.getElementById('lb')?.remove());
}

/** Poll pipeline status. Uses native setTimeout so it survives browser flakiness. */
async function pollPipeline(
  page: Page,
  check: (d: any) => boolean,
  maxMs = 300_000,
) {
  const t0 = Date.now();
  while (Date.now() - t0 < maxMs) {
    try {
      const r = await page.request.get(`${API}/pipeline/status`);
      if (r.ok()) { const d = await r.json(); if (check(d)) return d; }
    } catch { /* ignore */ }
    await p(page, 3000);
  }
  return null;
}

async function taskId(page: Page, idx: number): Promise<string> {
  const ids = page.locator('.task-id');
  if ((await ids.count()) > idx) return ((await ids.nth(idx).textContent()) || `Task ${idx+1}`).trim();
  return `Task ${idx+1}`;
}


// ═══════════════════════════════════════════════════════════════
//  TEST
// ═══════════════════════════════════════════════════════════════

test.describe('Demo Showcase', () => {
  test('Full app walkthrough', async ({ page }) => {
    test.setTimeout(7_200_000);

    // ── PROLOGUE: reset ──
    await page.goto('/dashboard');
    await expect(page.locator('mat-toolbar').first()).toBeVisible({ timeout: 15_000 });
    await page.request.post(`${API}/pipeline/cancel`).catch(() => {});
    await p(page, 1500);
    await page.request.post(`${API}/reset/execute`, {
      data: { phase_ids: ['triage', 'plan'], cascade: false },
    }).catch(() => {});
    await p(page, P);
    const t0 = Date.now();

    // ── SPLASH ──
    await splash(page);


    // ═════════════════════════════════════════════════════════
    //  CHAPTER 1 — THE PLATFORM
    // ═════════════════════════════════════════════════════════

    await chapter(page, 1, 'The Platform',
      'SDLC Pilot — nine automated phases from codebase understanding to delivery');

    await expect(page.locator('.hero')).toBeVisible({ timeout: 10_000 });
    await p(page, RP);
    await sub(page, 'SDLC Pilot automates the entire development lifecycle — from codebase analysis to implementation-ready plans', RP);
    await hideSub(page);
    await sub(page, 'Runs 100% on-premises — powered by your own LLM infrastructure, no data leaves your network', RP);
    await hideSub(page);

    const grid = page.locator('.phase-grid');
    if (await grid.isVisible({ timeout: 5000 }).catch(() => false)) {
      await grid.evaluate(e => e.scrollIntoView({ behavior: 'smooth', block: 'start' }));
      await p(page, P);
      await sub(page, 'Nine phases — each with its own icon — fully automated, zero manual intervention', LP);
      await hideSub(page);

      // Knowledge layer
      await layerBadge(page, 'Knowledge — understand the codebase', '#0369a1', LP);
      for (const [n, t] of [
        ['Discover', 'Scans the entire codebase and builds a searchable index'],
        ['Extract',  'Identifies components, dependencies, tech stack and interfaces'],
        ['Analyze',  'AI finds patterns, risks and architectural relationships'],
        ['Document', 'Generates arc42 chapters and C4 diagrams'],
      ] as const) {
        const c = page.locator(`.phase-card:has(.phase-name:has-text("${n}"))`).first();
        if (await c.isVisible({ timeout: 1500 }).catch(() => false)) {
          await c.evaluate(e => e.scrollIntoView({ behavior: 'smooth', block: 'center' }));
          await p(page, 300);
          await phaseTip(page, n, t, RP);
        }
      }
      await hideLayer(page);

      // Reasoning layer
      await layerBadge(page, 'Reasoning — analyze Jira tickets', '#6d28d9', LP);
      for (const [n, t] of [
        ['Triage', 'Reads a Jira ticket and gives the developer full context'],
        ['Plan',   'Creates a step-by-step plan with affected files and risks'],
      ] as const) {
        const c = page.locator(`.phase-card:has(.phase-name:has-text("${n}"))`).first();
        if (await c.isVisible({ timeout: 1500 }).catch(() => false)) {
          await c.evaluate(e => e.scrollIntoView({ behavior: 'smooth', block: 'center' }));
          await p(page, 300);
          await phaseTip(page, n, t, RP);
        }
      }
      await hideLayer(page);

      // Execution layer
      await layerBadge(page, 'Execution — generate and deliver', '#065f46', LP);
      for (const [n, t] of [
        ['Implement', 'Generates the actual code changes based on the plan'],
        ['Verify',    'Validates the generated code against quality standards'],
        ['Deliver',   'Packages everything into a ready-to-review deliverable'],
      ] as const) {
        const c = page.locator(`.phase-card:has(.phase-name:has-text("${n}"))`).first();
        if (await c.isVisible({ timeout: 1500 }).catch(() => false)) {
          await c.evaluate(e => e.scrollIntoView({ behavior: 'smooth', block: 'center' }));
          await p(page, 300);
          await phaseTip(page, n, t, RP);
        }
      }
      await hideLayer(page);
    }
    await scrollTop(page);


    // ═════════════════════════════════════════════════════════
    //  CHAPTER 2 — ARCHITECTURE KNOWLEDGE
    // ═════════════════════════════════════════════════════════

    await chapter(page, 2, 'Architecture Knowledge',
      'The AI builds a deep understanding of your codebase automatically');

    await page.goto('/knowledge');
    await page.locator('.stats-bar').waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {});
    await p(page, P);
    await sub(page, 'A structured knowledge base — built automatically from the codebase', LP);

    const extChip = page.locator('.group-chip:has-text("Extract")');
    if (await extChip.isVisible({ timeout: 3000 }).catch(() => false)) {
      await hideSub(page);
      await extChip.click();
      await p(page, P);
      await sub(page, '18 structured categories — components, dependencies, interfaces, and more', LP);
      await scrollDown(page, 400, 1500);
    }

    const docChip = page.locator('.group-chip:has-text("Document")');
    if (await docChip.isVisible({ timeout: 3000 }).catch(() => false)) {
      await hideSub(page);
      await docChip.click();
      await p(page, P);
      await sub(page, 'Full architecture documentation — generated entirely by AI', LP);
    }
    await hideSub(page);
    await scrollTop(page);


    // ═════════════════════════════════════════════════════════
    //  CHAPTER 3 — ARCHITECTURE DOCUMENTS
    // ═════════════════════════════════════════════════════════

    await chapter(page, 3, 'Architecture Documents',
      'Professional documentation — fully AI-generated');

    await page.goto('/reports');
    const firstGroup = page.locator('.doc-group-header').first();
    await firstGroup.waitFor({ state: 'visible', timeout: 15_000 }).catch(() => {});
    await p(page, P);

    const archTab = page.getByRole('tab', { name: /Architecture/i });
    const archText = await archTab.textContent().catch(() => '');
    const archCount = archText?.match(/\((\d+)\)/)?.[1] || '20+';

    const groups = page.locator('.doc-group-header');
    const gCount = await groups.count();

    if (gCount > 0) {
      await sub(page, `${archCount} architecture documents — AI-generated, production-ready`, LP);
      await hideSub(page);

      // arc42 group
      await groups.first().click();
      await p(page, LP);
      await sub(page, 'arc42 — the industry standard for software architecture documentation', LP);
      await hideSub(page);

      // Show 2-3 docs with scroll
      const fileRows = page.locator('.doc-file-row');
      await fileRows.first().waitFor({ state: 'visible', timeout: 5000 }).catch(() => {});
      const nDocs = Math.min(await fileRows.count(), 3);

      for (let i = 0; i < nDocs; i++) {
        const row = page.locator('.doc-file-row').nth(i);
        if (!(await row.isVisible({ timeout: 2000 }).catch(() => false))) continue;

        const name = await row.locator('.doc-file-name').textContent().catch(() => `Doc ${i+1}`);
        await row.click();
        await p(page, LP);

        const md = page.locator('.rendered-md').first();
        if (await md.isVisible({ timeout: 3000 }).catch(() => false)) {
          await sub(page, `${name?.trim()} — fully AI-authored`, RP);
          await md.evaluate(el => el.scrollTo({ top: el.scrollHeight * 0.4, behavior: 'smooth' }));
          await p(page, LP);
          await md.evaluate(el => el.scrollTo({ top: el.scrollHeight * 0.8, behavior: 'smooth' }));
          await p(page, P);
          await hideSub(page);
        }
        // close
        await page.locator('.doc-file-row').nth(i).click().catch(() => {});
        await p(page, FP);
      }
      await groups.first().click(); // close arc42
      await p(page, FP);
    }

    // C4 group
    if (gCount > 1) {
      await groups.nth(1).click();
      await p(page, LP);
      await sub(page, 'C4 architecture diagrams — system context, containers, and components', RP);

      const c4Row = page.locator('.doc-file-row').first();
      if (await c4Row.isVisible({ timeout: 3000 }).catch(() => false)) {
        await c4Row.click();
        await p(page, P);
        const md = page.locator('.rendered-md').first();
        if (await md.isVisible({ timeout: 3000 }).catch(() => false)) {
          await md.evaluate(el => el.scrollTo({ top: el.scrollHeight * 0.5, behavior: 'smooth' }));
          await p(page, LP);
        }
        await c4Row.click().catch(() => {});
        await p(page, FP);
      }
      await hideSub(page);
      await groups.nth(1).click(); // close C4
      await p(page, FP);
    }


    // ═════════════════════════════════════════════════════════
    //  CHAPTER 4 — INPUTS + RUN PIPELINE
    // ═════════════════════════════════════════════════════════

    await chapter(page, 4, 'Run the Pipeline',
      'The AI processes real Jira tickets — in parallel');

    // -- Inputs --
    await page.goto('/inputs');
    await page.locator('.categories-grid, .category-card').first()
      .waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {});
    await sub(page, 'Inputs — this is where your Jira tickets and project documentation are uploaded', RP);
    await hideSub(page);

    // Stats bar — total file count
    const statsBar = page.locator('.stats-bar');
    if (await statsBar.isVisible({ timeout: 3000 }).catch(() => false)) {
      await sub(page, 'Input files organized by category — tasks, requirements, and supplementary documentation', DR);
      await hideSub(page);
    }

    // Category cards
    const catCards = page.locator('.category-card');
    const nCats = await catCards.count();
    if (nCats > 0) {
      // Highlight the tasks category
      const tasksCard = page.locator('.category-card').filter({ hasText: /task/i }).first();
      if (await tasksCard.isVisible({ timeout: 2000 }).catch(() => false)) {
        await tasksCard.evaluate(e => e.scrollIntoView({ behavior: 'smooth', block: 'center' }));
        await p(page, P);
        await sub(page, 'Jira tickets exported as XML — the AI reads each one and builds a complete development brief', DR);
        await hideSub(page);
      }
      // Scroll to show all categories
      await scrollDown(page, 400, 2000);
      await sub(page, 'Each category accepts specific file formats — drop files here before running the pipeline', RP);
      await hideSub(page);
    }

    // -- Settings --
    await page.goto('/settings');
    await p(page, LP);
    await sub(page, 'Settings — configure the target repository and LLM connection', RP);
    await hideSub(page);

    // General tab — repository path
    await sub(page, 'Target repository — SDLC Pilot analyses this exact codebase to understand your architecture', DR);
    await hideSub(page);
    await scrollDown(page, 300, 1500);

    // LLM tab
    const llmTab = page.getByRole('tab', { name: /LLM/i });
    if (await llmTab.isVisible({ timeout: 3000 }).catch(() => false)) {
      await llmTab.click();
      await p(page, LP);
      await sub(page, 'LLM configuration — connects to your on-premises language model, no external API calls', DR);
      await hideSub(page);
    }

    await scrollTop(page);

    // -- Run Pipeline --
    await page.goto('/run');
    await p(page, 3000); // wait for async data (presets, tasks)

    await page.locator('.config-card').waitFor({ state: 'visible', timeout: 10_000 });
    await p(page, P);
    await sub(page, 'Run Pipeline — configure preset, parallelism, and task selection', RP);
    await hideSub(page);

    // 1. Select preset (retry if options not loaded yet)
    const matSelect = page.locator('.config-card mat-select');
    await matSelect.waitFor({ state: 'visible', timeout: 5000 });

    let presetOk = false;
    for (let attempt = 0; attempt < 3 && !presetOk; attempt++) {
      await matSelect.click();
      await p(page, LP);
      const opt = page.locator('mat-option').filter({ hasText: /Triage \+ Plan/i }).first();
      if (await opt.isVisible({ timeout: 3000 }).catch(() => false)) {
        await opt.click();
        await p(page, LP);
        presetOk = true;
      } else {
        await page.keyboard.press('Escape');
        await p(page, 2000);
      }
    }
    await sub(page, 'Preset selected: Triage and Plan — optimised for parallel execution', RP);
    await hideSub(page);

    // 2. Enable parallel + select tasks
    const parSec = page.locator('.parallel-section');
    if (await parSec.isVisible({ timeout: 5000 }).catch(() => false)) {
      // Enable parallel via the toggle
      const active = await page.locator('.parallel-section.parallel-active').isVisible().catch(() => false);
      if (!active) {
        const toggle = parSec.locator('mat-slide-toggle').first();
        if (await toggle.isVisible({ timeout: 2000 }).catch(() => false)) {
          await toggle.click();
          await p(page, P);  // P=800ms, was LP=1500ms
        }
      }
      await sub(page, 'Parallel processing enabled — tickets are analysed concurrently', LP);  // LP, was RP
      await hideSub(page);

      // Set concurrency to 2x
      const chip2x = page.locator('.concurrency-chip').filter({ hasText: '2x' }).first();
      if (await chip2x.isVisible({ timeout: 3000 }).catch(() => false)) {
        await chip2x.click();
        await p(page, FP);  // FP=500ms, was P=800ms
      }
      await sub(page, 'Concurrency set to 2x — maximum throughput for this workload', LP);  // LP, was RP
      await hideSub(page);

      // Verify tasks are selected — onParallelToggle auto-selects, but verify
      const selCount = await page.locator('.task-chip.selected').count().catch(() => 0);
      if (selCount === 0) {
        const selAll = page.locator('.task-picker-toggle');
        if (await selAll.isVisible({ timeout: 3000 }).catch(() => false)) {
          await selAll.click();
          await p(page, FP);
        } else {
          const chips = page.locator('.task-chip');
          for (let i = 0; i < await chips.count(); i++) {
            await chips.nth(i).click();
            await p(page, 200);
          }
        }
      }

      const nSel = await page.locator('.task-chip.selected').count().catch(() => 0);
      if (nSel > 0) {
        await sub(page, `${nSel} tasks selected — each processed as an independent pipeline`, LP);  // LP, was RP
        await hideSub(page);
      }
    }

    // 3. Click Run
    const runBtn = page.locator('button.run-btn');
    await runBtn.scrollIntoViewIfNeeded();
    await p(page, FP);  // FP=500ms, was P=800ms
    await sub(page, 'Initiating pipeline execution…', FP);  // FP, was P
    await hideSub(page);
    await runBtn.dispatchEvent('click');
    await p(page, LP);  // LP=1500ms, was 3000ms

    // 4. Verify started — API fallback if GUI click missed
    let started = await pollPipeline(page, d => d.state === 'running' || d.state === 'completed', 10_000);
    if (!started) {
      await page.request.post(`${API}/pipeline/run`, {
        data: { phases: ['triage','plan'], task_ids: ['BNUVZ-12529','BNUVZ-12568'], max_parallel: 2 },
      }).catch(() => {});
      started = await pollPipeline(page, d => d.state === 'running' || d.state === 'completed', 15_000);
    }

    // 5. Show running state — pipeline UI + use wait time to show Metrics + History
    if (started) {
      await scrollTop(page);
      await sub(page, 'Pipeline is running — both tickets are being processed in parallel', LP);

      const tGrid = page.locator('.task-progress-grid');
      if (await tGrid.isVisible({ timeout: 5000 }).catch(() => false)) {
        await hideSub(page);
        await tGrid.scrollIntoViewIfNeeded();
        await sub(page, 'Real-time progress per ticket — triage followed by planning', LP);
      }

      const logs = page.locator('.log-container, .virtual-log, cdk-virtual-scroll-viewport');
      if (await logs.first().isVisible({ timeout: 3000 }).catch(() => false)) {
        await hideSub(page);
        await logs.first().scrollIntoViewIfNeeded();
        await sub(page, 'Complete execution log — every AI decision is recorded for full traceability', LP);
      }

      // Dashboard interlude — show running stepper with progress ring
      await hideSub(page);
      await p(page, P);
      await page.goto('/dashboard');
      await p(page, LP);

      const stepperCard = page.locator('.stepper-card');
      if (await stepperCard.isVisible({ timeout: 5000 }).catch(() => false)) {
        await sub(page, 'Live dashboard — rotating border glow and progress ring show real-time pipeline state', DR);
        await hideSub(page);
      }

      // Show phase cards with running glow
      const runningCard = page.locator('.phase-running').first();
      if (await runningCard.isVisible({ timeout: 3000 }).catch(() => false)) {
        await runningCard.evaluate(e => e.scrollIntoView({ behavior: 'smooth', block: 'center' }));
        await sub(page, 'Running phases pulse with a blue shimmer — you always know what is executing', RP);
        await hideSub(page);
      }

      // Quick visit to MCP Servers
      await page.goto('/mcps');
      await p(page, LP);
      await sub(page, 'MCP Servers — Model Context Protocol integrations that give AI agents access to external tools', DR);
      await hideSub(page);
      await sub(page, 'Each MCP provides specialised capabilities — filesystem access, web search, sequential thinking, and more', DR);
      await hideSub(page);
      await scrollDown(page, 400, 2000);
      await p(page, P);

      // Quick visit to Collectors
      await page.goto('/collectors');
      await p(page, LP);
      await sub(page, 'Collectors — deterministic scanners that extract structured facts from the codebase', DR);
      await hideSub(page);
      await sub(page, 'Each collector targets a specific dimension — components, dependencies, interfaces, error handling, and more', DR);
      await hideSub(page);

      // Highlight 2 example rows (no content expand)
      const collectorRows = page.locator('.collector-row');
      const nRows = await collectorRows.count();
      if (nRows >= 2) {
        const row0 = collectorRows.nth(0);
        await row0.evaluate(e => {
          e.scrollIntoView({ behavior: 'smooth', block: 'center' });
          (e as HTMLElement).style.outline = '2px solid #12abdb';
          (e as HTMLElement).style.outlineOffset = '2px';
        });
        const name0 = await row0.locator('.collector-name').textContent().catch(() => 'Collector');
        await sub(page, `Example: ${name0?.trim()} — automatically discovers and catalogues architecture facts`, RP);
        await row0.evaluate(e => { (e as HTMLElement).style.outline = ''; (e as HTMLElement).style.outlineOffset = ''; });
        await hideSub(page);

        const row1 = collectorRows.nth(1);
        await row1.evaluate(e => {
          e.scrollIntoView({ behavior: 'smooth', block: 'center' });
          (e as HTMLElement).style.outline = '2px solid #12abdb';
          (e as HTMLElement).style.outlineOffset = '2px';
        });
        const name1 = await row1.locator('.collector-name').textContent().catch(() => 'Collector');
        await sub(page, `Example: ${name1?.trim()} — feeds structured data into the AI analysis pipeline`, RP);
        await row1.evaluate(e => { (e as HTMLElement).style.outline = ''; (e as HTMLElement).style.outlineOffset = ''; });
        await hideSub(page);
      }

      // Quick visit to History
      await page.goto('/history');
      await p(page, LP);
      await sub(page, 'Full audit trail — every pipeline run with inputs, outputs, and timestamps', RP);
      await hideSub(page);
      await scrollDown(page, 300, 1500);
      await p(page, P);

      // Return to run page
      await page.goto('/run');
      await p(page, LP);
    }
    await scrollTop(page);
    await hideSub(page);


    // ═════════════════════════════════════════════════════════
    //  CHAPTER 5 — TRIAGE RESULTS
    // ═════════════════════════════════════════════════════════

    await chapter(page, 5, 'Triage Results',
      'Each ticket analysed in full context — business impact, architecture, and risks');

    // Wait for at least one triage behind the chapter card
    const triageDone = await pollPipeline(page, d => {
      if (['completed','failed'].includes(d.state)) return true;
      const tp = d.task_progress || {};
      return Object.values(tp).some((t: any) => (t.completed_phases || []).includes('triage'));
    }, 300_000);

    if (!triageDone || triageDone.state === 'failed') {
      await sub(page, 'Pipeline did not complete — check LLM connectivity', DR);
      await hideSub(page);
    } else {
      // Dashboard first — show triage completed state
      await page.goto('/dashboard');
      await expect(page.locator('.hero')).toBeVisible({ timeout: 10_000 });
      await p(page, LP);
      await sub(page, 'Triage phase completed — both tickets have been analysed by the AI', RP);
      await hideSub(page);

      // Scroll to phase cards to show completed triage
      const triageCard = page.locator('.phase-card:has(.phase-name:has-text("Triage"))').first();
      if (await triageCard.isVisible({ timeout: 3000 }).catch(() => false)) {
        await triageCard.evaluate(e => e.scrollIntoView({ behavior: 'smooth', block: 'center' }));
        await p(page, P);
        await sub(page, 'Triage completed — now let\'s look at what the AI discovered', RP);
        await hideSub(page);
      }

      // Navigate to tasks page
      await page.goto('/tasks');
      await p(page, LP);

      const cards = page.locator('.task-card');
      await cards.first().waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {});
      await p(page, P);

      const nCards = await cards.count();
      if (nCards > 0) {
        // ── First task: focused walkthrough ──
        const id1 = await taskId(page, 0);
        await cards.first().click();
        await p(page, LP);

        await scrollEl(page, '.summary-grid');
        await sub(page, `${id1} — Priority, classification, and business impact at a glance`, RP);
        await hideSub(page);

        await scrollH4(page, 'Big Picture');
        await sub(page, 'Big Picture — what this ticket is about and why it matters to the business', DR);
        await hideSub(page);

        await scrollH4(page, 'Scope Boundary');
        await sub(page, 'Scope Boundary — what must change and what must not be touched', RP);
        await hideSub(page);

        // Smooth scroll through Architecture + Questions + Boundaries in one flow
        await scrollDown(page, 600, 3000);
        await sub(page, 'Architecture walkthrough, anticipated questions, and risk boundaries — all AI-generated', DR);
        await hideSub(page);

        await scrollDown(page, 600, 3000);
        await sub(page, 'Affected components and technical constraints identified automatically', RP);
        await hideSub(page);

        await scrollTop(page);

        // Back
        const back = page.locator('button:has(mat-icon:has-text("arrow_back"))');
        if (await back.isVisible({ timeout: 2000 }).catch(() => false)) {
          await back.click();
          await p(page, LP);
        } else {
          await page.goto('/tasks');
          await p(page, LP);
        }

        // ── Second task: quick overview ──
        const cards2 = page.locator('.task-card');
        if ((await cards2.count()) > 1) {
          const id2 = await taskId(page, 1);
          await cards2.nth(1).click();
          await p(page, LP);

          await scrollEl(page, '.summary-grid');
          await sub(page, `${id2} — same analytical depth, processed simultaneously`, RP);
          await hideSub(page);

          await scrollH4(page, 'Big Picture');
          await sub(page, `${id2} — strategic context and developer orientation`, RP);
          await hideSub(page);

          await scrollDown(page, 800, 4000);
          await sub(page, `${id2} — full triage with questions, risks, and affected components`, RP);
          await hideSub(page);

          await scrollTop(page);
        }
      }
    }


    // ── Run Pipeline: watch live terminal while plan executes ──
    await hideSub(page);

    await page.goto('/run');
    await p(page, LP);
    await sub(page, 'Run Pipeline — live terminal shows each phase executing in real time', RP);
    await hideSub(page);

    const planDone = await pollPipeline(page, d => {
      // State fully terminal
      if (['completed','failed'].includes(d.state)) return true;
      // All tasks done even if subprocess hasn't exited yet
      if (d.parallel_mode && d.task_progress) {
        const tasks = Object.values(d.task_progress) as any[];
        if (tasks.length > 0 && tasks.every((t: any) => ['completed','failed'].includes(t.state))) return true;
      }
      return false;
    }, 300_000);

    // Pipeline done — go straight to Development Plans, no time wasted

    // ═════════════════════════════════════════════════════════
    //  CHAPTER 6 — DEVELOPMENT PLANS
    // ═════════════════════════════════════════════════════════

    await chapter(page, 6, 'Development Plans',
      'Structured, actionable implementation plans — ready for the development team');

    if (!planDone || planDone.state === 'failed') {
      await sub(page, 'Pipeline did not complete — check LLM connectivity', DR);
      await hideSub(page);
    } else {
      await page.goto('/reports');
      await page.locator('.doc-group-header').first()
        .waitFor({ state: 'visible', timeout: 15_000 }).catch(() => {});
      await p(page, P);
      await sub(page, 'Reports page — all generated documentation organised by category', RP);
      await hideSub(page);

      const planTab = page.getByRole('tab', { name: /Development Plans/i });
      if (await planTab.isVisible({ timeout: 5000 }).catch(() => false)) {
        await planTab.click();
        await p(page, LP);
        await sub(page, 'Development Plans tab — one structured plan per task, ready for the team', RP);
        await hideSub(page);

        const ph0 = page.getByRole('button', { name: /BNUVZ-12529/ });
        const ph1 = page.getByRole('button', { name: /BNUVZ-12568/ });
        await ph0.or(ph1).first().waitFor({ state: 'visible', timeout: 10_000 }).catch(() => {});
        const has0 = await ph0.isVisible().catch(() => false);
        const has1 = await ph1.isVisible().catch(() => false);

        // First plan: focused walkthrough
        if (has0) {
          const lbl = (await ph0.locator('.mono').textContent().catch(() => null) ?? 'BNUVZ-12529').trim();
          await ph0.click();
          await p(page, LP);

          await scrollEl(page, '.overview-card');
          await sub(page, `${lbl} — Complexity assessment, estimated file changes, and effort`, DR);
          await hideSub(page);

          await sub(page, `${lbl} — Requirements, affected files, and implementation steps`, RP);
          await scrollDown(page, 700, 3000);
          await hideSub(page);

          await sub(page, `${lbl} — Step-by-step implementation with precise instructions per file`, RP);
          await scrollDown(page, 700, 3000);
          await hideSub(page);

          await sub(page, `${lbl} — Component dependencies and residual risks`, RP);
          await scrollDown(page, 700, 3000);
          await hideSub(page);

          await scrollTop(page);
          await ph0.click();
          await p(page, FP);
        }

        // Second plan: quick overview
        if (has1) {
          const lbl = (await ph1.locator('.mono').textContent().catch(() => null) ?? 'BNUVZ-12568').trim();
          await ph1.click();
          await p(page, LP);

          await scrollEl(page, '.overview-card');
          await sub(page, `${lbl} — Same depth, generated concurrently with the first ticket`, RP);
          await hideSub(page);

          await sub(page, `${lbl} — Requirements, files, and implementation steps`, RP);
          await scrollDown(page, 700, 3000);
          await hideSub(page);

          await sub(page, `${lbl} — Risks and component dependencies`, RP);
          await scrollDown(page, 700, 3000);
          await hideSub(page);

          await scrollTop(page);
          await ph1.click();
          await p(page, FP);
        }
      }

      // Export ZIP
      const expBtn = page.locator('button:has-text("Export ZIP")');
      if (await expBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await sub(page, 'One-click export — architecture docs, triage reports, and development plans packaged for the team', LP);
        await expBtn.click();
        await p(page, P);
      }
      await hideSub(page);
    }


    // ═════════════════════════════════════════════════════════
    //  FINALE
    // ═════════════════════════════════════════════════════════

    // Dashboard beauty shot — completed stepper
    await page.goto('/dashboard');
    await expect(page.locator('.hero')).toBeVisible({ timeout: 10_000 });
    await p(page, LP);

    const completedStepper = page.locator('.stepper-completed, .stepper-card');
    if (await completedStepper.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      await sub(page, 'All phases completed — full pipeline run visible at a glance', RP);
      await hideSub(page);
    }

    // Show activity rows (clickable)
    const actRow = page.locator('.activity-row').first();
    if (await actRow.isVisible({ timeout: 3000 }).catch(() => false)) {
      await actRow.evaluate(e => e.scrollIntoView({ behavior: 'smooth', block: 'center' }));
      await sub(page, 'Activity history — click any row for the full run details', RP);
      await hideSub(page);
    }
    await scrollTop(page);
    await p(page, P);

    const durSec = Math.round((Date.now() - t0) / 1000);
    const durLabel = durSec < 60 ? `${durSec}s` : `${Math.floor(durSec/60)}m ${durSec%60}s`;

    await page.evaluate(({ ac, dur }) => {
      document.getElementById('sub')?.remove();
      document.getElementById('ch')?.remove();
      const d = document.createElement('div');
      d.id = 'ch';
      Object.assign(d.style, {
        position:'fixed',inset:'0',zIndex:'100000',
        background:'linear-gradient(135deg,#001B3D,#002B5C)',
        display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',
        fontFamily:'system-ui,sans-serif',color:'#fff',transition:'opacity .8s',
      });
      d.innerHTML = `
        <div style="font-size:14px;font-weight:600;letter-spacing:3px;text-transform:uppercase;color:#12abdb;margin-bottom:28px">Results</div>
        <div style="font-size:34px;font-weight:600;margin-bottom:40px;text-align:center;max-width:700px;line-height:1.4">
          From a Jira ticket to an implementation-ready development plan — entirely automated
        </div>
        <div style="display:flex;gap:48px;margin-bottom:40px">
          <div style="text-align:center">
            <div style="font-size:42px;font-weight:700;color:#12abdb">${ac}</div>
            <div style="font-size:14px;color:rgba(255,255,255,.5);margin-top:4px">Architecture Docs</div>
          </div>
          <div style="text-align:center">
            <div style="font-size:42px;font-weight:700;color:#12abdb">2</div>
            <div style="font-size:14px;color:rgba(255,255,255,.5);margin-top:4px">Triage Reports</div>
          </div>
          <div style="text-align:center">
            <div style="font-size:42px;font-weight:700;color:#12abdb">2</div>
            <div style="font-size:14px;color:rgba(255,255,255,.5);margin-top:4px">Development Plans</div>
          </div>
          <div style="text-align:center">
            <div style="font-size:42px;font-weight:700;color:#12abdb">${dur}</div>
            <div style="font-size:14px;color:rgba(255,255,255,.5);margin-top:4px">Total Time</div>
          </div>
        </div>
        <div style="background:rgba(18,171,219,.12);border:1px solid rgba(18,171,219,.3);border-radius:12px;padding:16px 32px;margin-bottom:24px;text-align:center">
          <div style="font-size:13px;color:rgba(255,255,255,.5);margin-bottom:6px;letter-spacing:1px;text-transform:uppercase">Time saved vs. manual analysis</div>
          <div style="font-size:22px;font-weight:600;color:#fff">4–8 hours of senior developer time <span style="color:#12abdb">→ automated</span></div>
        </div>
        <div style="font-size:16px;color:rgba(255,255,255,.4);margin-bottom:32px">
          100% on-premises — source code and tickets never leave your infrastructure
        </div>
        <div style="display:flex;align-items:center;gap:12px;opacity:.6">
          
          <span style="width:1px;height:14px;background:rgba(255,255,255,.2)"></span>
          <span style="font-size:14px;font-style:italic;color:rgba(255,255,255,.5);letter-spacing:.5px">Make it real</span>
        </div>`;
      document.body.appendChild(d);
    }, { ac: archCount, dur: durLabel });

    await p(page, 5000);
    await page.evaluate(() => {
      const d = document.getElementById('ch');
      if (d) { d.style.opacity = '0'; setTimeout(() => d.remove(), 800); }
    });
    await p(page, 1000);

    // Final dashboard — already shown in beauty shot, just land here
    await page.goto('/dashboard');
    await expect(page.locator('.hero')).toBeVisible({ timeout: 10_000 });
    await p(page, RP);
  });
});
