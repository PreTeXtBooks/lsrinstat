# PreTeXt Book Features Guide

## Overview

This PreTeXt version of *Learning Statistics with R* includes several key features that make it suitable for teaching statistics with R:

## 1. R Code Support

### Basic Code Blocks

R code can be included using the `<program>` element with `language="r"`:

```xml
<program language="r">
  <input>
# Your R code here
x <- 10
y <- 20
x + y
  </input>
</program>
```

**Note**: In XML, you must use `&lt;` for `<` and `&gt;` for `>` characters.

### Code Listings with Captions

For numbered code examples with captions:

```xml
<listing xml:id="unique-id">
  <caption>Description of the code</caption>
  <program language="r">
    <input>
# Your R code
    </input>
  </program>
</listing>
```

### Interactive Code (Future Enhancement)

While the skeleton supports marking code as interactive with `interactive="yes"`, 
full interactivity would require integration with services like JupyterLite or RStudio Cloud.

## 2. Code Toggles (Knowls)

PreTeXt provides "knowls" - collapsible content blocks that allow readers to show/hide content.

### Toggling R Code Listings

R code blocks wrapped in a `<listing>` element are collapsible by default in this book (configured via `listing="yes"` in `publication/publication.ptx`). This lets readers show or hide standalone R code examples with a single click.

```xml
<listing xml:id="listing-unique-id">
  <caption>Description of the R code</caption>
  <program language="r">
    <input>
# Your R code here
# Note: in PreTeXt XML, the R assignment operator <- must be escaped as &lt;-
x &lt;- 10
y &lt;- 20
x + y
    </input>
  </program>
</listing>
```

The caption serves as the clickable toggle label. When the reader clicks it, the code block expands to show (or collapses to hide) the R code.

### Examples with Solutions

```xml
<example xml:id="example-id">
  <title>Example Title</title>
  <statement>
    <p>Problem statement...</p>
  </statement>
  <solution>
    <p>Solution content...</p>
    <program language="r">
      <input>
# Solution code
      </input>
    </program>
  </solution>
</example>
```

Solutions are hidden by default and can be revealed by clicking.

### Exercises with Hints and Solutions

```xml
<exercise xml:id="exercise-id">
  <statement>
    <p>Exercise prompt...</p>
  </statement>
  <hint>
    <p>Helpful hint...</p>
  </hint>
  <solution>
    <p>Complete solution...</p>
  </solution>
</exercise>
```

Both hints and solutions appear as clickable links that reveal content when clicked.

## 3. Image Support

### Including Static Images

Images can be placed in `source/images/` or `assets/` directories:

```xml
<figure xml:id="fig-unique-id">
  <caption>Description of the figure</caption>
  <image source="filename.jpg" width="50%">
    <description>Alt text for accessibility</description>
  </image>
</figure>
```

### Supported Image Formats

- PNG (.png)
- JPEG (.jpg, .jpeg)
- SVG (.svg) - recommended for diagrams and plots
- PDF (.pdf) - for LaTeX output

### R-Generated Plots

When R code generates plots, the resulting images can be saved and included in the document. 
Future enhancements could include automated plot generation during the build process.

## 4. GitHub Actions Deployment

The workflow in `.github/workflows/deploy-pretext.yml` automatically:

1. Installs PreTeXt CLI
2. Builds the HTML version of the book
3. Deploys to GitHub Pages (on main branch only)

### Configuration Notes

- Triggered on pushes to `main` branch
- Triggered on pull request events (builds but doesn't deploy)
- Can be manually triggered from the Actions tab
- Deploys to GitHub Pages only on main branch pushes (requires Pages to be enabled in repository settings)

## 5. Mathematical Content

PreTeXt fully supports LaTeX math:

```xml
<p>
  Inline math: <m>x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}</m>
</p>

<p>
  Display math:
  <me>
    \bar{x} = \frac{1}{n}\sum_{i=1}^{n} x_i
  </me>
</p>
```

## 6. Cross-References

Reference other parts of the book:

```xml
<p>
  See <xref ref="example-mean-calculation"/> for details.
</p>
```

This creates a hyperlink to the referenced element.

## 7. Publication Options

Configured in `publication/publication.ptx`:

- **HTML output**: Optimized for web viewing
- **PDF output**: Via LaTeX (requires LaTeX installation)
- **Chunking**: Controls how the book is split into pages
- **Numbering**: Controls chapter, section, and exercise numbering
- **Knowls**: Configure which elements are collapsible

## Next Steps

1. Add more chapters from the original book content
2. Convert existing R code examples to PreTeXt format
3. Include plots and figures from the original content
4. Configure custom styling if desired
5. Set up automated R code execution (optional future enhancement)

## Resources

- [PreTeXt Documentation](https://pretextbook.org/documentation.html)
- [PreTeXt Guide](https://pretextbook.org/doc/guide/html/)
- [PreTeXt Showcase](https://pretextbook.org/examples.html)
