import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';

import { marked } from 'marked';
import { ApiService, KnowledgeFile, KnowledgeSummary } from '../../services/api.service';

interface FileCategory {
  label: string;
  icon: string;
  description: string;
  files: KnowledgeFile[];
}

@Component({
  selector: 'app-knowledge',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatTableModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatTabsModule,
    MatTooltipModule,
  ],
  template: `
    <div class="page-container">
      <h1 class="page-title">
        <mat-icon>psychology</mat-icon>
        Knowledge Explorer
      </h1>

      @if (loading) {
        <div class="loading-center">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      } @else if (summary) {
        <!-- Stats Bar -->
        <div class="stats-bar">
          <div class="stat-item">
            <mat-icon>inventory_2</mat-icon>
            <strong>{{ summary.total_files }}</strong> files
          </div>
          <div class="stat-item">
            <mat-icon>storage</mat-icon>
            <strong>{{ formatBytes(summary.total_size_bytes) }}</strong>
          </div>
          @for (tc of typeCounts; track tc.type) {
            <div class="stat-item stat-type" [class]="'stat-' + tc.type">
              <mat-icon>{{ fileIcon(tc.type) }}</mat-icon>
              <strong>{{ tc.count }}</strong> {{ tc.label }}
            </div>
          }
        </div>

        <!-- Category Tabs -->
        <mat-tab-group animationDuration="200ms" (selectedTabChange)="onTabChange($event.index)">
          @for (cat of categories; track cat.label) {
            <mat-tab>
              <ng-template mat-tab-label>
                <mat-icon class="tab-icon">{{ cat.icon }}</mat-icon>
                {{ cat.label }}
                <span class="tab-count">{{ cat.files.length }}</span>
              </ng-template>

              <div class="tab-body">
                @if (cat.files.length === 0) {
                  <div class="empty-inline">
                    <mat-icon>folder_open</mat-icon>
                    <span>No files in this category.</span>
                  </div>
                } @else {
                  <div class="file-grid">
                    @for (file of cat.files; track file.path) {
                      <div class="file-card" [class.file-active]="selectedFile === file" (click)="viewFile(file)">
                        <div class="file-card-top">
                          <mat-icon class="fc-icon" [class]="'type-' + file.type">
                            {{ fileIcon(file.type) }}
                          </mat-icon>
                          <div class="fc-meta">
                            <div class="fc-name">{{ file.name }}</div>
                            <div class="fc-path">{{ file.path }}</div>
                          </div>
                        </div>
                        <div class="file-card-bottom">
                          <span class="fc-badge" [class]="'badge-' + file.type">{{ file.type }}</span>
                          <span class="fc-size">{{ formatBytes(file.size_bytes) }}</span>
                        </div>
                      </div>
                    }
                  </div>
                }
              </div>
            </mat-tab>
          }
        </mat-tab-group>

        <!-- Document Viewer -->
        @if (selectedFile) {
          <div class="viewer-panel">
            <div class="viewer-header">
              <div class="viewer-title">
                <mat-icon [class]="'type-' + selectedFile.type">{{ fileIcon(selectedFile.type) }}</mat-icon>
                <span>{{ selectedFile.name }}</span>
                <span class="viewer-badge" [class]="'badge-' + selectedFile.type">{{ selectedFile.type }}</span>
              </div>
              <div class="viewer-actions">
                @if (viewMode !== 'rendered' && canRender(selectedFile)) {
                  <button mat-stroked-button (click)="viewMode = 'rendered'" class="mode-btn">
                    <mat-icon>visibility</mat-icon> Rendered
                  </button>
                }
                @if (viewMode !== 'source') {
                  <button mat-stroked-button (click)="viewMode = 'source'" class="mode-btn">
                    <mat-icon>code</mat-icon> Source
                  </button>
                }
                <button mat-icon-button (click)="closeViewer()" matTooltip="Close">
                  <mat-icon>close</mat-icon>
                </button>
              </div>
            </div>
            <div class="viewer-body">
              @if (fileLoading) {
                <div class="loading-center">
                  <mat-spinner diameter="32"></mat-spinner>
                </div>
              } @else if (viewMode === 'rendered' && renderedHtml) {
                <div class="rendered-content markdown-body" [innerHTML]="renderedHtml"></div>
              } @else {
                <pre class="source-content code-viewer">{{ selectedContent }}</pre>
              }
            </div>
          </div>
        }
      } @else {
        <div class="empty-state">
          <mat-icon>psychology</mat-icon>
          <p>No knowledge base found. Run the pipeline (Phases 0-2) to generate architecture facts.</p>
        </div>
      }
    </div>
  `,
  styles: [
    `
      /* Stats */
      .stats-bar {
        display: flex;
        gap: 10px;
        margin-bottom: 20px;
        flex-wrap: wrap;
      }
      .stat-item {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 8px 14px;
        background: #fff;
        border-radius: 10px;
        font-size: 13px;
        color: var(--cg-gray-500);
      }
      .stat-item .mat-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
        color: var(--cg-blue);
      }
      .stat-item strong {
        color: var(--cg-gray-900);
      }
      .stat-json .mat-icon {
        color: var(--cg-vibrant);
      }
      .stat-md .mat-icon {
        color: var(--cg-blue);
      }
      .stat-drawio .mat-icon {
        color: var(--cg-success);
      }
      .stat-html .mat-icon {
        color: #e44d26;
      }

      /* Tabs */
      .tab-icon {
        font-size: 18px;
        width: 18px;
        height: 18px;
        margin-right: 6px;
      }
      .tab-count {
        margin-left: 6px;
        background: var(--cg-gray-100);
        color: var(--cg-gray-500);
        font-size: 11px;
        font-weight: 600;
        padding: 1px 7px;
        border-radius: 10px;
      }
      .tab-body {
        padding: 16px 0;
      }

      /* File Grid */
      .file-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 10px;
      }
      .file-card {
        background: #fff;
        border-radius: 10px;
        padding: 14px;
        cursor: pointer;
        border: 2px solid transparent;
        transition:
          border-color 0.15s,
          box-shadow 0.15s;
      }
      .file-card:hover {
        border-color: rgba(0, 112, 173, 0.15);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
      }
      .file-active {
        border-color: var(--cg-blue) !important;
        box-shadow: 0 0 0 1px var(--cg-blue) !important;
      }
      .file-card-top {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        margin-bottom: 10px;
      }
      .fc-icon {
        font-size: 22px;
        width: 22px;
        height: 22px;
        flex-shrink: 0;
        margin-top: 1px;
      }
      .type-json {
        color: var(--cg-vibrant);
      }
      .type-md {
        color: var(--cg-blue);
      }
      .type-drawio {
        color: var(--cg-success);
      }
      .type-html {
        color: #e44d26;
      }
      .type-adoc {
        color: #a0522d;
      }
      .type-confluence {
        color: #0052cc;
      }
      .type-other {
        color: var(--cg-gray-500);
      }
      .fc-meta {
        min-width: 0;
        flex: 1;
      }
      .fc-name {
        font-size: 13px;
        font-weight: 600;
        color: var(--cg-gray-900);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .fc-path {
        font-size: 11px;
        color: var(--cg-gray-500);
        font-family: monospace;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .file-card-bottom {
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
      .fc-badge {
        display: inline-block;
        padding: 1px 8px;
        border-radius: 8px;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.4px;
      }
      .badge-json {
        background: rgba(18, 171, 219, 0.1);
        color: var(--cg-vibrant);
      }
      .badge-md {
        background: rgba(0, 112, 173, 0.1);
        color: var(--cg-blue);
      }
      .badge-drawio {
        background: rgba(40, 167, 69, 0.1);
        color: var(--cg-success);
      }
      .badge-html {
        background: rgba(228, 77, 38, 0.1);
        color: #e44d26;
      }
      .badge-adoc {
        background: rgba(160, 82, 45, 0.1);
        color: #a0522d;
      }
      .badge-confluence {
        background: rgba(0, 82, 204, 0.1);
        color: #0052cc;
      }
      .badge-other {
        background: var(--cg-gray-100);
        color: var(--cg-gray-500);
      }
      .fc-size {
        font-size: 11px;
        color: var(--cg-gray-500);
      }

      /* Viewer Panel */
      .viewer-panel {
        margin-top: 20px;
        background: #fff;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      }
      .viewer-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 20px;
        background: var(--cg-gray-50);
        border-bottom: 1px solid var(--cg-gray-100);
      }
      .viewer-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
        font-weight: 500;
      }
      .viewer-badge {
        padding: 1px 8px;
        border-radius: 8px;
        font-size: 10px;
        font-weight: 700;
        text-transform: uppercase;
      }
      .viewer-actions {
        display: flex;
        align-items: center;
        gap: 6px;
      }
      .mode-btn {
        font-size: 12px !important;
        line-height: 28px !important;
        padding: 0 10px !important;
      }
      .mode-btn .mat-icon {
        font-size: 16px;
        width: 16px;
        height: 16px;
        margin-right: 4px;
      }
      .viewer-body {
        max-height: 70vh;
        overflow: auto;
      }

      /* Source Code */
      .source-content {
        margin: 0;
        background: var(--cg-dark);
        color: #eeffff;
        padding: 20px;
        white-space: pre-wrap;
        word-break: break-all;
        font-size: 12px;
        line-height: 1.7;
        min-height: 200px;
      }

      /* Rendered Markdown */
      .rendered-content {
        padding: 24px 32px;
        font-size: 14px;
        line-height: 1.7;
        color: var(--cg-gray-900);
      }

      /* DrawIO info */
      .drawio-info {
        text-align: center;
        padding: 32px 24px;
      }
      .drawio-icon-large {
        margin-bottom: 16px;
      }
      .drawio-info h3 {
        font-size: 18px;
        margin: 0 0 8px;
      }
      .drawio-meta {
        font-size: 13px;
        color: var(--cg-gray-500);
        margin: 0 0 8px;
      }
      .drawio-hint {
        font-size: 13px;
        color: var(--cg-gray-500);
        margin: 0 0 16px;
      }
      .drawio-preview {
        text-align: left;
      }

      /* Empty inline */
      .empty-inline {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 32px 16px;
        color: var(--cg-gray-500);
        font-size: 14px;
      }
      .empty-inline .mat-icon {
        color: var(--cg-gray-200);
      }
    `,
  ],
})
export class KnowledgeComponent implements OnInit {
  summary: KnowledgeSummary | null = null;
  categories: FileCategory[] = [];
  typeCounts: { type: string; label: string; count: number }[] = [];
  selectedFile: KnowledgeFile | null = null;
  selectedContent: string | null = null;
  renderedHtml: SafeHtml | null = null;
  viewMode: 'source' | 'rendered' = 'rendered';
  loading = true;
  fileLoading = false;

  constructor(
    private api: ApiService,
    private cdr: ChangeDetectorRef,
    private sanitizer: DomSanitizer,
  ) {}

  ngOnInit(): void {
    this.api.getKnowledgeFiles().subscribe({
      next: (s) => {
        this.summary = s;
        this.buildCategories(s.files);
        this.buildTypeCounts(s.files);
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loading = false;
        this.cdr.markForCheck();
      },
    });
  }

  private buildCategories(files: KnowledgeFile[]): void {
    const arc42 = files.filter((f) => f.path.includes('arc42'));
    const c4 = files.filter((f) => f.path.includes('c4\\') || f.path.includes('c4/'));
    const containerAnalysis = files.filter((f) => f.path.includes('container_analysis'));
    const devPlans = files.filter((f) => f.path.includes('development'));
    const facts = files.filter(
      (f) =>
        f.type === 'json' &&
        !f.path.includes('container_analysis') &&
        !f.path.includes('development') &&
        !f.path.includes('test_run') &&
        (f.path.startsWith('architecture\\') || f.path.startsWith('architecture/')),
    );
    const other = files.filter(
      (f) =>
        !arc42.includes(f) &&
        !c4.includes(f) &&
        !containerAnalysis.includes(f) &&
        !devPlans.includes(f) &&
        !facts.includes(f),
    );

    this.categories = [
      {
        label: 'Arc42 Docs',
        icon: 'menu_book',
        description: 'Architecture documentation (arc42 template)',
        files: this.sortArc42(arc42),
      },
      {
        label: 'C4 Model',
        icon: 'account_tree',
        description: 'C4 architecture model (context, container, component, deployment)',
        files: c4,
      },
      {
        label: 'Knowledge Base',
        icon: 'data_object',
        description: 'Architecture facts, components, relations, patterns',
        files: facts,
      },
      {
        label: 'Containers',
        icon: 'dns',
        description: 'Per-container analysis (backend, frontend, e2e, import, jsApi)',
        files: containerAnalysis,
      },
      { label: 'Dev Plans', icon: 'assignment', description: 'Generated development plans', files: devPlans },
      { label: 'Other', icon: 'folder', description: 'Other knowledge files', files: other },
    ].filter((c) => c.files.length > 0);
  }

  private sortArc42(files: KnowledgeFile[]): KnowledgeFile[] {
    return files.sort((a, b) => {
      const numA = parseInt(a.name.match(/^(\d+)/)?.[1] || '99');
      const numB = parseInt(b.name.match(/^(\d+)/)?.[1] || '99');
      if (numA !== numB) return numA - numB;
      return a.name.localeCompare(b.name);
    });
  }

  private buildTypeCounts(files: KnowledgeFile[]): void {
    const counts = new Map<string, number>();
    for (const f of files) {
      counts.set(f.type, (counts.get(f.type) || 0) + 1);
    }
    const labels: Record<string, string> = {
      json: 'JSON',
      md: 'Markdown',
      drawio: 'DrawIO',
      html: 'HTML',
      adoc: 'AsciiDoc',
      confluence: 'Wiki',
      other: 'Other',
    };
    this.typeCounts = [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([type, count]) => ({ type, label: labels[type] || type, count }));
  }

  onTabChange(_index: number): void {
    this.closeViewer();
  }

  viewFile(file: KnowledgeFile): void {
    this.selectedFile = file;
    this.fileLoading = true;
    this.selectedContent = null;
    this.renderedHtml = null;
    this.viewMode = this.canRender(file) ? 'rendered' : 'source';
    this.cdr.markForCheck();

    this.api.getKnowledgeFile(file.path).subscribe({
      next: (content) => {
        const text = typeof content === 'string' ? content : JSON.stringify(content, null, 2);
        this.selectedContent = text;
        if (this.canRender(file)) {
          this.renderContent(file, text, content);
        }
        this.fileLoading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.selectedContent = 'Error loading file';
        this.fileLoading = false;
        this.cdr.markForCheck();
      },
    });
  }

  private renderContent(file: KnowledgeFile, text: string, raw: unknown): void {
    if (file.type === 'md') {
      const html = marked.parse(text) as string;
      this.renderedHtml = this.sanitizer.bypassSecurityTrustHtml(html);
    } else if (file.type === 'html') {
      this.renderedHtml = this.sanitizer.bypassSecurityTrustHtml(text);
    } else if (file.type === 'json') {
      const highlighted = this.highlightJson(text);
      this.renderedHtml = this.sanitizer.bypassSecurityTrustHtml(`<pre class="json-viewer">${highlighted}</pre>`);
    } else if (file.type === 'adoc') {
      // Simple AsciiDoc rendering (headings, bold, links, code)
      const html = this.renderAsciidoc(text);
      this.renderedHtml = this.sanitizer.bypassSecurityTrustHtml(html);
    } else if (file.type === 'drawio') {
      // DrawIO XML — show diagram metadata and info
      const html = this.renderDrawioInfo(text, file.name);
      this.renderedHtml = this.sanitizer.bypassSecurityTrustHtml(html);
    } else if (file.type === 'confluence') {
      // Confluence wiki markup — render basic formatting
      const html = this.renderConfluence(text);
      this.renderedHtml = this.sanitizer.bypassSecurityTrustHtml(html);
    }
  }

  private highlightJson(json: string): string {
    return json
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"([^"\\]*(\\.[^"\\]*)*)"\s*:/g, '<span class="json-key">"$1"</span>:')
      .replace(/:\s*"([^"\\]*(\\.[^"\\]*)*)"/g, ': <span class="json-string">"$1"</span>')
      .replace(/:\s*(\d+\.?\d*)/g, ': <span class="json-number">$1</span>')
      .replace(/:\s*(true|false)/g, ': <span class="json-bool">$1</span>')
      .replace(/:\s*(null)/g, ': <span class="json-null">$1</span>');
  }

  canRender(file: KnowledgeFile): boolean {
    return ['md', 'html', 'json', 'adoc', 'drawio', 'confluence'].includes(file.type);
  }

  private renderAsciidoc(text: string): string {
    // Simple AsciiDoc to HTML conversion
    const html = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      // Headers: = Title, == Section, === Subsection
      .replace(/^={4}\s+(.+)$/gm, '<h4>$1</h4>')
      .replace(/^={3}\s+(.+)$/gm, '<h3>$1</h3>')
      .replace(/^={2}\s+(.+)$/gm, '<h2>$1</h2>')
      .replace(/^=\s+(.+)$/gm, '<h1>$1</h1>')
      // Bold: *text*
      .replace(/\*([^*]+)\*/g, '<strong>$1</strong>')
      // Italic: _text_
      .replace(/_([^_]+)_/g, '<em>$1</em>')
      // Code: `text`
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      // Links: link:url[label]
      .replace(/link:([^[]+)\[([^\]]+)\]/g, '<a href="$1">$2</a>')
      // Lists: * item
      .replace(/^\*\s+(.+)$/gm, '<li>$1</li>')
      // Tables: |cell|cell|
      .replace(/^\|(.+)\|$/gm, (match, content) => {
        const cells = content
          .split('|')
          .map((c: string) => `<td>${c.trim()}</td>`)
          .join('');
        return `<tr>${cells}</tr>`;
      })
      // Paragraphs
      .replace(/\n\n/g, '</p><p>');
    return `<div class="markdown-body"><p>${html}</p></div>`;
  }

  private renderDrawioInfo(xml: string, filename: string): string {
    // Parse DrawIO XML to extract diagram info
    const cellCount = (xml.match(/<mxCell/g) || []).length;
    const hasLayers = xml.includes('mxGraphModel');
    return `
      <div class="drawio-info">
        <div class="drawio-icon-large">
          <svg width="64" height="64" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#F08705"/>
          <text x="32" y="42" fill="white" font-size="24" font-weight="bold" text-anchor="middle">.io</text></svg>
        </div>
        <h3>${filename}</h3>
        <p class="drawio-meta">${cellCount} elements | DrawIO XML diagram</p>
        <p class="drawio-hint">Open this file in <strong>draw.io</strong> or <strong>diagrams.net</strong> for interactive editing.</p>
        <div class="drawio-preview">
          <pre class="json-viewer">${xml.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').substring(0, 2000)}${xml.length > 2000 ? '\n...(truncated)' : ''}</pre>
        </div>
      </div>`;
  }

  private renderConfluence(text: string): string {
    const lines = text.split('\n');
    let html = '';
    let inTable = false;
    let inCode = false;

    for (const line of lines) {
      const trimmed = line.trim();

      // Code blocks: {code} ... {code} or {code:lang} ... {code}
      if (/^\{code(:.*)?\}$/.test(trimmed)) {
        if (inCode) {
          html += '</code></pre>';
          inCode = false;
        } else {
          if (inTable) {
            html += '</tbody></table>';
            inTable = false;
          }
          html += '<pre class="json-viewer"><code>';
          inCode = true;
        }
        continue;
      }
      if (inCode) {
        html += this.escHtml(line) + '\n';
        continue;
      }

      // Horizontal rule: ----
      if (trimmed === '----') {
        if (inTable) {
          html += '</tbody></table>';
          inTable = false;
        }
        html += '<hr>';
        continue;
      }

      // Headers: h1. to h6.
      const hm = trimmed.match(/^h([1-6])\.\s+(.+)$/);
      if (hm) {
        if (inTable) {
          html += '</tbody></table>';
          inTable = false;
        }
        html += `<h${hm[1]}>${this.cfInline(this.escHtml(hm[2]))}</h${hm[1]}>`;
        continue;
      }

      // Table header row: ||col||col||
      if (/^\|\|.+\|\|$/.test(trimmed)) {
        if (!inTable) {
          html += '<table><tbody>';
          inTable = true;
        }
        const cells = trimmed
          .slice(2, -2)
          .split('||')
          .map((c) => `<th>${this.cfInline(this.escHtml(c.trim()))}</th>`)
          .join('');
        html += `<tr>${cells}</tr>`;
        continue;
      }

      // Table data row: |col|col|  (not starting with ||)
      if (/^\|[^|].+\|$/.test(trimmed)) {
        if (!inTable) {
          html += '<table><tbody>';
          inTable = true;
        }
        const cells = trimmed
          .slice(1, -1)
          .split('|')
          .map((c) => `<td>${this.cfInline(this.escHtml(c.trim()))}</td>`)
          .join('');
        html += `<tr>${cells}</tr>`;
        continue;
      }

      // End table if the line is not a table row
      if (inTable) {
        html += '</tbody></table>';
        inTable = false;
      }

      // Unordered list: * item
      if (/^\*\s+/.test(trimmed)) {
        html += `<li>${this.cfInline(this.escHtml(trimmed.replace(/^\*\s+/, '')))}</li>`;
        continue;
      }

      // Ordered list: # item
      if (/^#\s+/.test(trimmed)) {
        html += `<li>${this.cfInline(this.escHtml(trimmed.replace(/^#\s+/, '')))}</li>`;
        continue;
      }

      // Empty line
      if (trimmed === '') {
        continue;
      }

      // Regular paragraph
      html += `<p>${this.cfInline(this.escHtml(trimmed))}</p>`;
    }

    if (inTable) html += '</tbody></table>';
    if (inCode) html += '</code></pre>';

    return `<div class="markdown-body">${html}</div>`;
  }

  private escHtml(s: string): string {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  private cfInline(s: string): string {
    return s
      .replace(/\{\{([^}]+)\}\}/g, '<code>$1</code>')
      .replace(/\*([^*]+)\*/g, '<strong>$1</strong>')
      .replace(/_([^_]+)_/g, '<em>$1</em>')
      .replace(/\[([^\]|]+)\|([^\]]+)\]/g, '<a href="$2">$1</a>')
      .replace(/\[([^\]]+)\]/g, '<a href="$1">$1</a>');
  }

  closeViewer(): void {
    this.selectedFile = null;
    this.selectedContent = null;
    this.renderedHtml = null;
  }

  fileIcon(type: string): string {
    switch (type) {
      case 'json':
        return 'data_object';
      case 'md':
        return 'article';
      case 'drawio':
        return 'architecture';
      case 'html':
        return 'web';
      case 'adoc':
        return 'description';
      case 'confluence':
        return 'edit_document';
      default:
        return 'insert_drive_file';
    }
  }

  formatBytes(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  countByType(type: string): number {
    return this.summary?.files.filter((f) => f.type === type).length || 0;
  }
}
