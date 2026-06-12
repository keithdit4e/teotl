# Research Agent Skills

Essential capabilities for gathering and analyzing information from the web.

## Core Skills

### web

**What it does:**
- Search the web using search engines
- Access public websites and articles
- Find academic papers and research
- Look up documentation and references
- Read news articles and blog posts
- Access open data sources

**When to use:**
- Primary research tool
- Finding multiple sources
- Looking up facts and statistics
- Checking recent news and updates
- Accessing documentation

**Limitations:**
- Cannot access paywalled content
- Limited to publicly available information
- Subject to search engine capabilities
- May not find very recent (<24 hours) content

**Example tasks:**
```
"Search for recent AI agent developments"
"Find academic papers on transformer models"
"Look up market size data for SaaS industry"
"Check recent news about [company/topic]"
```

### filesystem

**What it does:**
- Save research reports to files
- Create and manage bibliographies
- Store source lists and notes
- Organize research by topic
- Read previously saved research

**When to use:**
- Saving completed research reports
- Creating reference documents
- Organizing findings
- Building knowledge base

**Limitations:**
- Subject to security policy (see security.yaml)
- Cannot access system or sensitive directories

**Example tasks:**
```
"Save this research report to ~/Research/ai-agents.md"
"Create a bibliography file with all sources"
"Store this source list for future reference"
```

## Skill Combinations

### Standard Research (Recommended)
```bash
teotl chat --agent research-agent --skills web,filesystem
```
**Best for:** All research tasks with ability to save reports

### Web-Only Research
```bash
teotl chat --agent research-agent --skills web
```
**Best for:** Quick lookups, fact-checking without saving

## Research Capabilities

### What You Can Research

**Markets and Industries:**
- Market size and growth trends
- Industry forecasts
- Key players and market share
- Competitive landscape

**Companies and Products:**
- Company information and history
- Product features and pricing
- User reviews and ratings
- Competitive comparisons

**Technology:**
- Technical specifications
- Implementation guides
- Best practices
- Tool comparisons

**Academic Topics:**
- Research papers and studies
- Scientific findings
- Expert opinions
- Literature reviews

**Current Events:**
- Recent news and developments
- Trending topics
- Event coverage
- Updates and announcements

### Source Types Available

**Academic:**
- Google Scholar
- arXiv preprints
- Academic institution websites
- Research databases (open access)

**Industry:**
- Market research reports (free versions)
- Industry analyst blogs
- Company reports and whitepapers
- Trade publications

**News:**
- Major news outlets
- Technology news sites
- Industry-specific publications
- Press releases

**Data:**
- Government statistics
- Public datasets
- Survey results
- Economic indicators

**Documentation:**
- Official product documentation
- API references
- Technical guides
- Tutorial sites

## Research Workflows

### Market Research Workflow

1. **Use web skill** to search for market size data
2. **Use web skill** to find industry reports
3. **Use web skill** to identify key players
4. **Use web skill** to check recent news/trends
5. Synthesize findings into report
6. **Use filesystem skill** to save report

### Competitive Analysis Workflow

1. **Use web skill** to research each competitor
2. **Use web skill** to find product information
3. **Use web skill** to look up pricing
4. **Use web skill** to find user reviews
5. Create comparison matrix
6. **Use filesystem skill** to save analysis

### Fact-Checking Workflow

1. **Use web skill** to find original source of claim
2. **Use web skill** to search for supporting evidence
3. **Use web skill** to search for contradicting evidence
4. **Use web skill** to check expert consensus
5. Assess credibility and make verdict
6. **Use filesystem skill** to save fact-check

### Literature Review Workflow

1. **Use web skill** to search academic databases
2. **Use web skill** to find relevant papers
3. **Use web skill** to check citations
4. **Use web skill** to find related work
5. Summarize findings and themes
6. **Use filesystem skill** to create bibliography

## Search Strategies

### Effective Search Techniques

**Be specific:**
```
❌ "AI"
✅ "large language model benchmarks 2023"

❌ "SaaS growth"
✅ "B2B SaaS CAC payback period benchmarks"
```

**Use operators:**
```
"exact phrase matching"
site:example.com (search specific site)
filetype:pdf (find PDFs)
intitle:"keyword" (in page title)
after:2023 (recent only)
```

**Try multiple searches:**
- Different keyword combinations
- Various search engines
- Academic vs general search
- News-specific search

### Finding Quality Sources

**Academic research:**
```
- Search Google Scholar
- Look for peer-reviewed journals
- Check citation counts
- Verify author credentials
```

**Industry data:**
```
- Look for analyst firms (Gartner, Forrester)
- Check industry associations
- Find company reports
- Use government statistics
```

**Recent developments:**
```
- Use news search
- Check company blogs
- Look for press releases
- Search social media (verified accounts)
```

## Limitations and Workarounds

### Paywall Content

**Challenge:** Many high-quality sources are behind paywalls

**Workarounds:**
- Look for preprint versions (arXiv)
- Check author's personal website
- Find alternative open-access sources
- Use article abstracts
- Find related free content

### Outdated Information

**Challenge:** Some topics have outdated search results

**Workarounds:**
- Add year to search queries
- Use "after:YYYY" operator
- Check "News" search mode
- Look for "updated" dates
- Verify with multiple sources

### Conflicting Information

**Challenge:** Different sources provide different information

**Approach:**
- Evaluate source credibility
- Check publication dates
- Look for consensus
- Note disagreements explicitly
- Present multiple perspectives

### No Information Available

**Challenge:** Very niche or new topics may lack sources

**Approach:**
- Broaden search terms
- Look for related topics
- Check adjacent industries
- Note the limitation
- Explain what's known

## Best Practices

### Source Evaluation

**Always check:**
- Author credentials
- Publication reputation
- Date published
- Citations/references
- Conflicts of interest
- Bias indicators

**Prefer:**
- Primary sources over secondary
- Recent over old (for current topics)
- Peer-reviewed over non-reviewed
- Multiple sources over single
- Data-backed over opinion

### Citation Management

**Track as you research:**
- Save full URLs
- Note publication dates
- Record author names
- Capture access dates
- Note page titles

**Cite properly:**
- Use consistent format (APA)
- Include all required elements
- Provide working URLs
- Update broken links

### Time Management

**Quick research (10-15 min):**
- 3-5 sources
- Focus on key findings
- Summary format

**Standard research (30-60 min):**
- 10-15 sources
- Comprehensive coverage
- Structured report

**Deep research (2+ hours):**
- 20+ sources
- Multi-angle analysis
- Full documentation

## Troubleshooting

### "Cannot find reliable sources"

**Fix:**
- Try different search terms
- Expand to related topics
- Look for older foundational sources
- Check if topic is too niche

### "Sources all say different things"

**Fix:**
- This is normal - present multiple views
- Evaluate source quality
- Look for consensus on core facts
- Note areas of legitimate debate

### "Information seems outdated"

**Fix:**
- Filter by date in search
- Check for updated versions
- Note the age limitation
- Supplement with recent news

### "Only finding marketing materials"

**Fix:**
- Add terms like "review", "comparison", "analysis"
- Use site: operator for non-vendor sites
- Look for academic or analyst sources
- Search for user communities

---

*These skills provide comprehensive research capabilities. Master web search techniques for best results.*
