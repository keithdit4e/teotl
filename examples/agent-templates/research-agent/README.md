# Research Agent Template

An intelligent research assistant that gathers information from the web, analyzes sources, synthesizes findings, and creates comprehensive reports - helping you make informed decisions faster.

## What This Agent Does

- **🔍 Web Research** - Search and analyze web sources systematically
- **📊 Data Synthesis** - Combine information from multiple sources
- **📝 Report Generation** - Create structured research reports
- **✅ Fact Checking** - Verify claims against multiple sources
- **📚 Source Management** - Track and cite sources properly
- **💡 Insight Extraction** - Identify key findings and trends
- **📈 Competitive Analysis** - Research competitors and market trends

## Quick Start

### 1. Set Up Your Research Agent

```bash
# Create workspace
mkdir -p ~/.teotl/agents/research-agent

# Copy template files
cp -r examples/agent-templates/research-agent/* ~/.teotl/agents/research-agent/
```

### 2. Customize Your Profile

Edit `~/.teotl/agents/research-agent/USER.md`:

- Your research interests and topics
- Preferred sources and domains
- Report formats you like
- Citation style preferences
- Research depth preferences

### 3. Start Your Research Agent

```bash
# Interactive mode
teotl chat --agent research-agent --skills web,filesystem

# The agent loads your preferences and research style
```

## Example Interactions

### Basic Research Query

```
You: "Research the benefits of remote work for software companies"

Agent: "I'll research this topic from multiple angles. Starting search...

**Search Strategy:**
1. Academic studies on remote work productivity
2. Industry reports from tech companies
3. Case studies from major software companies
4. Employee surveys and satisfaction data

Gathering sources... Found 15 relevant sources.

**Key Findings:**

**Productivity:**
- 85% of companies report maintained or increased productivity (Harvard Business Review, 2023)
- Average 13% performance increase observed (Stanford Study, 2022)
- Reduced distractions from office environment

**Employee Benefits:**
- 74% of workers prefer hybrid or remote options (Buffer State of Remote Work 2023)
- Average 2 hours saved per day on commuting
- Improved work-life balance reported by 78%

**Company Benefits:**
- 30% reduction in office costs (Global Workplace Analytics)
- Access to global talent pool
- Reduced employee turnover (25% decrease reported)

**Challenges:**
- Communication overhead
- Onboarding complexity
- Team cohesion requires intentional effort

Should I create a detailed report with all sources cited?"
```

### Competitive Analysis

```
You: "Who are the main competitors to Notion and what are their strengths?"

Agent: "Analyzing Notion's competitive landscape...

**Main Competitors:**

**1. Monday.com**
- Strength: Visual project management, customizable workflows
- Market Position: Strong in enterprise market
- Pricing: $8-16/user/month
- Key Differentiator: No-code automation builder

**2. Coda**
- Strength: Document-database hybrid, powerful formulas
- Market Position: Growing in product teams
- Pricing: Free - $30/user/month
- Key Differentiator: Connected data across docs

**3. Confluence**
- Strength: Enterprise integration, Atlassian ecosystem
- Market Position: Dominant in large enterprises
- Pricing: $5.75-$11/user/month
- Key Differentiator: Jira integration, established platform

**4. Airtable**
- Strength: Spreadsheet-database hybrid, API access
- Market Position: Strong in operations teams
- Pricing: Free - $45/user/month
- Key Differentiator: Structured data, automations

**Market Positioning:**
- Notion: All-in-one workspace, simplicity
- Competitors focus on specific use cases (project management, databases)

Would you like me to create a detailed comparison matrix?"
```

### Fact Checking

```
You: "Verify this claim: 'Coffee is the second most traded commodity in the world after oil'"

Agent: "Fact-checking this claim against multiple sources...

**Claim:** Coffee is the second most traded commodity after oil

**Verdict:** ❌ **FALSE** (Common misconception)

**Evidence:**

**Top 10 Traded Commodities (by value):**
1. Crude Oil
2. Natural Gas
3. Gold
4. Copper
5. Soybeans
6. Coffee (ranked 7th-10th depending on year)

**Sources:**
- World Bank Commodity Markets Report (2023)
- International Trade Centre data
- UN Comtrade statistics

**Where This Myth Originated:**
- Coffee WAS second most traded in the 1980s-1990s
- Frequently repeated statistic became outdated
- Often confused with "most consumed beverage"

**Accurate Statement:**
"Coffee is one of the most traded agricultural commodities, typically ranking in the top 10 globally."

Should I research the current coffee trade statistics in more detail?"
```

## Use Cases

### Market Research

Research markets, competitors, trends:

```bash
teotl chat --agent research-agent

> "Research the AI agent development tools market"
> "Who are the key players in this space?"
> "What are the emerging trends?"
> "Create a market analysis report"
```

### Academic Research

Gather information for papers or projects:

```bash
teotl chat --agent research-agent

> "Research recent papers on transformer neural networks"
> "Summarize the key innovations in the last 2 years"
> "Find seminal papers I should cite"
```

### Product Research

Research products, reviews, comparisons:

```bash
teotl chat --agent research-agent

> "Compare the top 5 project management tools"
> "What are users saying about Notion vs Obsidian?"
> "Research user pain points with current solutions"
```

### Technical Investigation

Deep dive into technical topics:

```bash
teotl chat --agent research-agent

> "Research best practices for API rate limiting"
> "Find case studies of companies handling scale"
> "What are the trade-offs of different approaches?"
```

## Customization Guide

### Research Depth

Edit `USER.md` to set your preferred depth:

```markdown
## Research Preferences

**Depth Level:** Comprehensive
- Sources per topic: 10-15
- Include academic papers: Yes
- Include industry reports: Yes
- Include news articles: Recent only (<6 months)

**Citation Style:** APA 7th Edition

**Report Format:**
- Executive summary (1-2 paragraphs)
- Key findings (bullet points)
- Detailed analysis (sections)
- Sources (full citations)
```

### Preferred Sources

Customize which sources to prioritize:

```markdown
## Trusted Sources

**Academic:**
- Google Scholar
- arXiv
- IEEE Xplore
- ACM Digital Library

**Industry:**
- Harvard Business Review
- MIT Technology Review
- TechCrunch
- The Verge

**Data:**
- Statista
- Pew Research
- Gartner
- Forrester
```

### Report Templates

Define custom report formats in `USER.md`:

```markdown
## Report Templates

**Market Analysis Template:**
1. Executive Summary
2. Market Size and Growth
3. Key Players
4. Trends and Drivers
5. Challenges
6. Opportunities
7. Recommendations

**Competitive Analysis Template:**
1. Competitor Overview
2. Feature Comparison
3. Pricing Analysis
4. Market Positioning
5. Strengths/Weaknesses
6. Strategic Recommendations
```

## Best Practices

### 1. Start with Clear Questions

```
❌ "Research AI"
✅ "Research the current state of AI code generation tools for Python"

❌ "Look up competitors"
✅ "Identify the top 5 direct competitors to Vercel and their key differentiators"
```

### 2. Specify Source Requirements

```
"Research X, focusing on academic papers from the last 3 years"
"Find industry reports from reputable sources (Gartner, Forrester, McKinsey)"
"Look for user reviews and testimonials, not marketing materials"
```

### 3. Request Structured Output

```
"Create a comparison table of features"
"Generate an executive summary with bullet points"
"Organize findings by category: benefits, challenges, opportunities"
```

### 4. Iterate on Findings

```
You: "Research AI safety concerns"
Agent: [Provides overview]

You: "Focus more on the technical challenges, less on policy"
Agent: [Refined research on technical aspects]

You: "Add information about current mitigation strategies"
Agent: [Expanded with solutions]
```

## Automation with Missions

Set up recurring research tasks:

```python
from forge.primitives.mission import Mission, MissionInterval

# Daily industry news summary
mission = Mission(
    description="Daily tech news summary",
    interval=MissionInterval.DAILY,
    instructions="""
    1. Search for tech news from the last 24 hours
    2. Filter for AI and developer tools topics
    3. Summarize top 5 stories
    4. Save to daily_news.md
    """,
    tools=["web", "filesystem"],
)

# Weekly competitive monitoring
mission = Mission(
    description="Weekly competitor analysis",
    interval=MissionInterval.WEEKLY,
    instructions="""
    1. Check competitor websites for product updates
    2. Search for news mentions
    3. Track pricing changes
    4. Update competitor_tracking.md
    """,
    tools=["web", "filesystem"],
)
```

## Skills Reference

### web
- Search engines and websites
- Academic databases
- News sources
- Industry reports
- Social media (public)

### filesystem
- Save research reports
- Manage source lists
- Create bibliographies
- Store findings

See `SKILLS.md` for detailed capabilities.

## Research Quality

### Source Evaluation Criteria

The agent evaluates sources based on:

**Authority:**
- Author credentials
- Publisher reputation
- Peer review status

**Accuracy:**
- Citations and references
- Data sources
- Fact-checkable claims

**Currency:**
- Publication date
- Information freshness
- Updates and revisions

**Objectivity:**
- Bias indicators
- Balanced perspective
- Conflicts of interest

### Multi-Source Verification

For important claims, the agent:
1. Finds 3+ independent sources
2. Checks for consensus
3. Notes disagreements
4. Evaluates source quality

## Troubleshooting

### "Cannot access paywall content"

**Limitation:** Agent cannot access paid subscriptions

**Alternatives:**
- Look for pre-prints or author's versions
- Find alternative free sources
- Use publicly available abstracts
- Check institutional access

### "Conflicting information found"

**Response:** Agent will present multiple perspectives:
```
**Conflicting Claims:**

Source A (Nature, 2023): "X is true"
- Evidence: [data]
- Methodology: [peer-reviewed]

Source B (TechCrunch, 2023): "X may not be true"
- Evidence: [industry feedback]
- Methodology: [interviews]

**Analysis:** Scientific consensus leans toward Source A, but practical implementation faces challenges noted in Source B.
```

### "Too much information"

**Fix:** Request focused research:
```
"Narrow down to the top 3 most important findings"
"Focus only on peer-reviewed academic sources"
"Summarize in 3 bullet points max"
```

### "Need more depth"

**Fix:** Request expanded research:
```
"Provide more details on the technical implementation"
"Include more examples and case studies"
"Add statistical analysis"
```

## Security & Privacy

### Web Access

**CAN access:**
- ✅ Public websites and databases
- ✅ Open-access publications
- ✅ Free tier resources
- ✅ Public social media

**CANNOT access:**
- ❌ Paywall content (subscriptions)
- ❌ Private user accounts
- ❌ Restricted databases
- ❌ Internal company data

### Data Privacy

From `security.yaml`:

- Research data stored locally only
- No personal data collection
- Browsing history not retained
- Search queries not logged externally

## Integration Examples

### Export to Markdown

```bash
teotl chat --agent research-agent

> "Research X and save a report to research_report.md"
> "Create a bibliography file with all sources"
> "Generate a summary slide deck in markdown"
```

### Integration with Note-Taking Apps

```bash
# Save to Obsidian vault
teotl chat --agent research-agent

> "Research X and save to ~/Obsidian/Research/topic.md"
> "Add tags and backlinks for Obsidian"
```

### API Integration

```python
# Use agent programmatically
from forge.core.agent import Agent

agent = Agent.load("research-agent")
result = await agent.run("Research emerging AI trends")

# Extract structured data
findings = result.data["key_findings"]
sources = result.data["sources"]
```

## Template Files

```
research-agent/
├── README.md           # This file
├── PERSONALITY.md      # Agent personality and style
├── USER.md             # Your research preferences
├── INSTRUCTIONS.md     # Research procedures
├── SKILLS.md           # Available capabilities
└── security.yaml       # Security policy
```

## Getting Help

- **Commands:** `/help` in chat mode
- **Skills:** `/skills` for capabilities
- **Feedback:** Share research quality feedback

---

**Start researching smarter:**

```bash
teotl chat --agent research-agent --skills web,filesystem
```

*Turn hours of research into minutes.*
