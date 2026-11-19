"use strict";

const assert = require("node:assert/strict");
const {execFileSync} = require("node:child_process");
const {readFileSync} = require("node:fs");
const {runInNewContext} = require("node:vm");

const window = {};
runInNewContext(readFileSync("frontend/math.js","utf8"), {window});
const render = window.ReplayMath.inline;

assert.match(render(String.raw`$x_1^2+\frac{1}{2}=\sqrt{9}$`), /<msubsup>.*<mfrac>.*<msqrt>/);
assert.match(render(String.raw`$$\overrightarrow{AB}\parallel\overrightarrow{CD}$$`), /<math display="block">.*→.*∥/);
assert.equal(render("<script>alert(1)</script>"), "&lt;script&gt;alert(1)&lt;/script&gt;");
assert.doesNotMatch(render(String.raw`$\text{<img>}$`), /<img>/);
assert.match(render(String.raw`$\deg(cx^m y^n)=m+n$`), /<mi mathvariant="normal">deg<\/mi>/);
assert.doesNotMatch(render(String.raw`$\deg(cx^m y^n)=m+n$`), /°/);
assert.match(render(String.raw`$90^\circ=90\degree$`), /<msup><mn>90<\/mn><mo>°<\/mo><\/msup>.*<mo>°<\/mo>/);
assert.match(render(String.raw`$\widetilde a-a$`), /<mover accent="true"><mi>a<\/mi><mo>~<\/mo><\/mover>/);
assert.match(render(String.raw`$S_{\triangle}=\frac{ah}{2}$`), /<msub>.*△.*<mfrac>/);

const source = String.raw`
import json
from backend.curriculum import TOPICS, generate, lesson
def texts(node):
    if isinstance(node, str):
        if "$" in node:
            yield node
    elif isinstance(node, dict):
        for value in node.values():
            yield from texts(value)
    elif isinstance(node, list):
        for value in node:
            yield from texts(value)
entries = set()
for topic in TOPICS:
    key = topic["id"]
    entries.update(texts(lesson(key)))
    for variant in range(topic["variants"]):
        entries.update(texts(generate(key, variant)))
print(json.dumps(sorted(entries)))
`;
const samples = JSON.parse(execFileSync("python",["-B","-c",source],{encoding:"utf8",maxBuffer:20*1024*1024}));
assert(samples.length>=60,"LaTeX curriculum samples are missing");
for(const source of samples){
  const html=render(source);
  assert.match(html,/<math[ >]/,source);
  assert.doesNotMatch(html,/class="math-source"/,source);
}
console.log("MathML samples rendered:",samples.length);
