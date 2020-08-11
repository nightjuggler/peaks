/* globals document, window */
/* exported enableTooltips */

const enableTooltips = (function() {
'use strict';

function positionTooltip(tooltip)
{
	tooltip.style.display = 'block';

	const arrowDiv = tooltip.lastElementChild;
	const arrowBox = arrowDiv.getBoundingClientRect();
	const tooltipBox = tooltip.getBoundingClientRect();

	let parent = tooltip.parentElement;
	const parentBox = parent.getBoundingClientRect();
	let parentLeft = 0;
	let parentTop = 0;

	while (parent && window.getComputedStyle(parent).position === 'static')
	{
		parentLeft += parent.offsetLeft;
		parentTop += parent.offsetTop;
		parent = parent.offsetParent;
	}

	let tooltipLeft = Math.round(parentLeft + parentBox.width / 2.0 - tooltipBox.width / 2.0);
	const tooltipTop = Math.round(parentTop + 2 - arrowBox.height - tooltipBox.height);
	let arrowLeft = Math.round((tooltipBox.width - arrowBox.width) / 2.0);

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
	const tooltips = event.currentTarget.getElementsByClassName('tooltip');
	positionTooltip(tooltips[0]);
	return false;
}
function hideTooltip(event)
{
	const tooltips = event.currentTarget.getElementsByClassName('tooltip');
	tooltips[0].style.display = 'none';
	return false;
}
function enableTooltips(element)
{
	for (const tooltip of element.getElementsByClassName('tooltip'))
	{
		if (tooltip.tooltipEnabled) continue;

		const arrowDiv = document.createElement('div');
		const arrow1 = document.createElement('div');
		const arrow2 = document.createElement('div');

		arrowDiv.className = 'tooltipArrowDiv';
		arrow1.className = 'tooltipArrow1';
		arrow2.className = 'tooltipArrow2';

		arrowDiv.appendChild(arrow1);
		arrowDiv.appendChild(arrow2);
		tooltip.appendChild(arrowDiv);

		const parent = tooltip.parentElement;
		parent.addEventListener('mouseenter', showTooltip);
		parent.addEventListener('mouseleave', hideTooltip);
		tooltip.tooltipEnabled = true;
	}
}
	window.addEventListener('DOMContentLoaded', () => enableTooltips(document.body));
	return enableTooltips;
})();
