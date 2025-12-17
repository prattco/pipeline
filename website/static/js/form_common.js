$(document).ready(function() {
    // $('input[required]').on('input', function () {
    //     if (this.validity.valid) {
    //         $(this).css('border', '1px solid');
    //     } else {
    //         $(this).css('border', '2px solid red');
    //     }
    // });
    $('.field-info').hover(
        function() {
        $('.tooltipbox').html($(this).attr("description"));
        $('.tooltipbox').show();
        }, function() {
        $('.tooltipbox').hide();
        }
    );

    $('.field-info').mousemove(function(e){
        var tooltipBox = $('.tooltipbox');
        var tooltipWidth = tooltipBox.outerWidth();
        var pageWidth = $(window).width();
        var xCoordinate = e.pageX + 10;
        var yCoordinate = e.pageY + 10;

        if (xCoordinate + tooltipWidth > pageWidth) {
            xCoordinate = e.pageX - tooltipWidth - 10;
        }
    
        tooltipBox.css({
            'top': yCoordinate,
            'left': xCoordinate
        });
    });

    if($("#page_method").val() == "modify") {
        $("input", $(".uneditable")).each(function(){
            $(this).attr("type", "hidden");
            $(this).after($(this).val());
        });
    }
});

function reloadSelect(id, options, nullable=true) {
    $('#' + id).empty();

    if(nullable) {
        $('#' + id).append($('<option></option>').val("").html("--"));
    }
    $.each(options, function(value, text) {
        $('#' + id).append($('<option></option>').val(value).html(text));
    });
}