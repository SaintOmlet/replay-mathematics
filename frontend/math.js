"use strict";

/* Offline MathML for the LaTeX commands used by Replay's curriculum. */
window.ReplayMath = (() => {
  const escape = value => String(value ?? "").replace(/[&<>"']/g, c => (
    {"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[c]
  ));
  const symbols = {
    cdot:"·", times:"×", div:"÷", pm:"±", mp:"∓", le:"≤", leq:"≤", ge:"≥", geq:"≥",
    ne:"≠", neq:"≠", approx:"≈", in:"∈", notin:"∉", subset:"⊂", cup:"∪", cap:"∩", to:"→",
    longrightarrow:"⟶", Rightarrow:"⇒", Longleftrightarrow:"⇔", iff:"⇔", mapsto:"↦", infty:"∞", pi:"π", alpha:"α", beta:"β",
    gamma:"γ", theta:"θ", Delta:"Δ", delta:"δ", lambda:"λ", phi:"φ", mu:"μ", sigma:"σ", omega:"ω",
    ldots:"…", dots:"…", cdots:"⋯", angle:"∠", perp:"⊥", parallel:"∥", sim:"∼", cong:"≅",
    degree:"°", circ:"°", sum:"∑", selected:"✓", vert:"|", langle:"⟨", rangle:"⟩",
    sin:"sin", cos:"cos", tan:"tan", tg:"tg", log:"log", ln:"ln", min:"min", max:"max", mod:"mod",
    percent:"%", varepsilon:"ε", epsilon:"ε", triangle:"△", cot:"cot"
  };
  const identifier = /^[A-Za-z\u0400-\u04ffα-ωΑ-Ω]+$/u;
  const op = text => "<mo>"+escape(text)+"</mo>";
  const row = text => "<mrow>"+text+"</mrow>";

  function formula(source, display=false) {
    let position=0;
    function readText() {
      if(source[position]!=="{") throw new Error("Expected a group");
      let end=source.indexOf("}",++position);
      if(end<0) throw new Error("Incomplete group");
      const text=source.slice(position,end);
      position=end+1;
      return text;
    }
    function skipSpace() {
      while(position<source.length&&/\s/u.test(source[position]))position++;
    }
    function atom() {
      skipSpace();
      let c=source[position++];
      if(!c) throw new Error("Incomplete expression");
      if(c==="{") {
        const interior=sequence("}");
        if(source[position++]!=="}") throw new Error("Unclosed group");
        return row(interior);
      }
      if(c==="\\") {
        const name=/^[a-zA-Z]+/.exec(source.slice(position))?.[0] || source[position++];
        if(!name) throw new Error("Incomplete command");
        if(/^[A-Za-z]+$/.test(name))position+=name.length;
        if(["left","right","displaystyle"].includes(name))return "";
        if([",",";",":"," ","!","quad","qquad"].includes(name))return '<mspace width=".28em"/>';
        if(["{","}","|","%","_","$"].includes(name))return op(name);
        if(["frac","dfrac","tfrac"].includes(name))return "<mfrac>"+atom()+atom()+"</mfrac>";
        if(name==="sqrt") {
          skipSpace();
          if(source[position]==="[") {
            position++;
            const index=sequence("]");
            if(source[position++]!=="]") throw new Error("Unclosed radical index");
            return "<mroot>"+atom()+row(index)+"</mroot>";
          }
          return "<msqrt>"+atom()+"</msqrt>";
        }
        if(name==="binom")return row(op("(")+'<mfrac linethickness="0">'+atom()+atom()+"</mfrac>"+op(")"));
        if(["overline","bar","vec","overrightarrow"].includes(name))
          return "<mover>"+atom()+op(name==="vec"||name==="overrightarrow"?"→":"¯")+"</mover>";
        if(name==="widetilde"||name==="tilde")return "<mover accent=\"true\">"+atom()+op("~")+"</mover>";
        if(name==="text"||name==="operatorname"||name==="mathrm"||name==="mathbb")return "<mtext>"+escape(readText())+"</mtext>";
        if(name==="underline")return "<munder>"+atom()+op("_")+"</munder>";
        if(name==="deg")return '<mi mathvariant="normal">deg</mi>';
        if(!(name in symbols)) throw new Error("Unsupported command");
        c=symbols[name];
      } else if(/[0-9]/u.test(c)) {
        const rest=/^[0-9]*(?:[.,][0-9]+)?/.exec(source.slice(position))[0];
        position+=rest.length;
        return "<mn>"+escape(c+rest)+"</mn>";
      }
      if(identifier.test(c))return "<mi>"+escape(c)+"</mi>";
      return op(c==="-"?"−":c);
    }
    function sequence(stop) {
      let output="";
      while(position<source.length&&source[position]!==stop) {
        skipSpace();
        if(position>=source.length||source[position]===stop)break;
        let body=atom();
        if(!body)continue;
        skipSpace();
        let superscript="",subscript="";
        while(source[position]==="^"||source[position]==="_") {
          const marker=source[position++];
          const index=atom();
          if(marker==="^")superscript=index;else subscript=index;
          skipSpace();
        }
        if(superscript&&subscript)body="<msubsup>"+body+subscript+superscript+"</msubsup>";
        else if(superscript)body="<msup>"+body+superscript+"</msup>";
        else if(subscript)body="<msub>"+body+subscript+"</msub>";
        output+=body;
      }
      return output;
    }
    if(source.length>500) return escape(source);
    try {
      const rendered=sequence();
      return '<math'+(display?' display="block"':'')+'>'+row(rendered)+"</math>";
    } catch {
      return '<span class="math-source">'+escape(source)+"</span>";
    }
  }

  function inline(text) {
    const chunks=String(text??"").split(/(\$\$[^\n]+?\$\$|\$[^$\n]+?\$)/gu);
    return chunks.map(part=>part.startsWith("$$")&&part.endsWith("$$")?formula(part.slice(2,-2),true):
      part.startsWith("$")&&part.endsWith("$")&&part.length>2?formula(part.slice(1,-1)):escape(part)).join("");
  }
  return Object.freeze({inline});
})();
