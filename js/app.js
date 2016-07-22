var main = function() {
	$('body').hide();
	$('body').fadeIn(1500);	

	$('.post-content').hide();

	$('.post-heading').click(function() {
		$('.post-content').addClass("disabled");
		content = $(this).siblings('.post-content');
		content.removeClass("disabled");
		$('.disabled').hide(
			function() {
				$('.disabled').animate({}, 1000);
			});
		content.toggle(
			function() {
				content.animate({}, 1000);
			});});
};

$(document).ready(main);