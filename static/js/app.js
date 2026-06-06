/**
 * 智能巡更系统 - 通用 JavaScript
 */

$(function () {
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function () {
        $('.alert-dismissible').fadeOut('slow');
    }, 5000);

    // Handle sidebar collapse toggle for mobile
    $('.sidebar .collapse').on('show.bs.collapse', function () {
        $(this).siblings('.nav-link').addClass('active');
    });

    $('.sidebar .collapse').on('hide.bs.collapse', function () {
        $(this).siblings('.nav-link').removeClass('active');
    });

    // Clean up modal backdrop if any leftover
    $(document).on('hidden.bs.modal', '#common-modal', function () {
        $('.modal-backdrop').remove();
        $('body').removeClass('modal-open');
    });
});

// ====== Common Modal Helpers ======

function showModal(title, bodyHtml, footerHtml) {
    $('#modal-title').text(title);
    $('#modal-body').html(bodyHtml);
    $('#modal-footer').html(footerHtml);
    var modal = new bootstrap.Modal('#common-modal');
    modal.show();
}

function hideModal() {
    var modal = bootstrap.Modal.getInstance('#common-modal');
    if (modal) modal.hide();
}
