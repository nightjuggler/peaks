/* globals document, window */
"use strict";

function positionTooltip(tooltip)
{
	tooltip.style.display = 'block';

	var arrowDiv = tooltip.lastElementChild;
	var arrowBox = arrowDiv.getBoundingClientRect();
	var tooltipBox = tooltip.getBoundingClientRect();

	var parent = tooltip.parentElement;
	var parentBox = parent.getBoundingClientRect();
	var parentLeft = 0;
	var parentTop = 0;

	while (parent)
	{
		var computedStyle = window.getComputedStyle(parent);
		if (computedStyle.position !== 'static') break;
		parentLeft += parent.offsetLeft;
		parentTop += parent.offsetTop;
		parent = parent.offsetParent;
	}

	var tooltipLeft = Math.round(parentLeft + parentBox.width / 2.0 - tooltipBox.width / 2.0);
	var tooltipTop = Math.round(parentTop + 2 - arrowBox.height - tooltipBox.height);
	var arrowLeft = Math.round((tooltipBox.width - arrowBox.width) / 2.0);

	if (tooltipLeft < 0)
	{
		arrowLeft += tooltipLeft;
		tooltipLeft = 0;
	}

	tooltip.style.left = tooltipLeft + 'px';
	tooltip.style.top = tooltipTop + 'px';
	arrowDiv.style.left = arrowLeft + 'px';
}
function showTooltip(event)
{
	var tooltips = event.currentTarget.getElementsByClassName('tooltip');
	positionTooltip(tooltips[0]);
	return false;
}
function hideTooltip(event)
{
	var tooltips = event.currentTarget.getElementsByClassName('tooltip');
	tooltips[0].style.display = 'none';
	return false;
}
function enableTooltips()
{
	var tooltips = document.getElementsByClassName('tooltip');

	for (var i = 0; i < tooltips.length; ++i)
	{
		var tooltip = tooltips[i];
		if (tooltip.tooltipEnabled) continue;

		var arrowDiv = document.createElement('div');
		var arrow1 = document.createElement('div');
		var arrow2 = document.createElement('div');

		arrowDiv.className = 'tooltipArrowDiv';
		arrow1.className = 'tooltipArrow1';
		arrow2.className = 'tooltipArrow2';

		arrowDiv.appendChild(arrow1);
		arrowDiv.appendChild(arrow2);
		tooltip.appendChild(arrowDiv);

		var parent = tooltip.parentElement;
		parent.addEventListener('mouseenter', showTooltip, false);
		parent.addEventListener('mouseleave', hideTooltip, false);
		tooltip.tooltipEnabled = true;
	}
}
window.addEventListener('DOMContentLoaded', enableTooltips, false);
