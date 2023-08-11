import { mathjax } from "mathjax-full/js/mathjax.js";
import { TeX } from "mathjax-full/js/input/tex.js";
import { SVG } from "mathjax-full/js/output/svg.js";
import { liteAdaptor } from "mathjax-full/js/adaptors/liteAdaptor.js";
import { RegisterHTMLHandler } from "mathjax-full/js/handlers/html.js";
import { AllPackages } from "mathjax-full/js/input/tex/AllPackages.js";  // Force preloading packages.
import yargs from "yargs/yargs";
import { hideBin } from "yargs/helpers";


function tex2svg(
    tex,
    extensions,
    inline
) {
    const documentOptions = {
        InputJax: new TeX({
            packages: extensions
        }),
        OutputJax: new SVG({
            fontCache: "none"
        })
    };
    const convertOption = {
        display: !inline
    };

    const adaptor = liteAdaptor();
    RegisterHTMLHandler(adaptor);
    const mathDocument = mathjax.document(tex, documentOptions);
    const mmlNode = mathDocument.convert(tex, convertOption);
    const svg = adaptor.innerHTML(mmlNode);
    return svg;
}


const argv = yargs(hideBin(process.argv)).argv;
console.log(tex2svg(
    argv.tex,
    argv.extensions.split(" "),
    argv.inline == "True"
));