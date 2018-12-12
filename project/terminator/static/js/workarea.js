
$("form.confirm").areYouSure({
    message: "Consider saving before leaving the page."
});


function updateWordCount(textarea) {
    if (textarea.value.length == 0) {
        words = 0;
    } else {
        words = Math.round((textarea.value.split(/\b/).length) / 2);
    }
    if (words < 50) {
        msg = "";
    } else {
        //TODO: i18n
        msg = words + " words";
    }
    msg = $("p#wordcount").text(msg);
}

$(function () {
    definition = document.getElementById("id_definition");
    if (definition.value.length) {
        updateWordCount(definition);
    }
});

$("#id_definition").on("input", function (e) {
    updateWordCount(e.target);
});
