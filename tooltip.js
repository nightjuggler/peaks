/* globals document, window */
/* exported enableTooltips */

const enableTooltips = (function() {
'use strict';

let activeTooltip;

const closedIcon = '\u25C4\uFE0E'; // black left-pointing pointer
const openIcon = '\u25B2'; // black up-pointing triangle

function positionTooltip(tooltip, parent)
{
	tooltip.style.display = 'block';

	const arrow = tooltip.lastElementChild;

	if (!parent) parent = tooltip.parentElement;

	let tooltipLeft = (parent.offsetWidth - tooltip.offsetWidth) / 2;
	let parentLeft = 0;
	let parentTop = 0;
	let parentStyle;

	while (parent && (parentStyle = window.getComputedStyle(parent)).position === 'static')
	{
		const borderLeft = +parentStyle.borderLeftWidth.slice(0, -2); // strip 'px'
		const borderTop = +parentStyle.borderTopWidth.slice(0, -2); // strip 'px'
		parentLeft += parent.offsetLeft + borderLeft;
		parentTop += parent.offsetTop + borderTop;
		parent = parent.offsetParent;
	}

	tooltipLeft += parentLeft;
	let arrowLeft = (tooltip.clientWidth - arrow.offsetWidth) / 2;
	let tooltipTop = parentTop - arrow.offsetHeight - tooltip.offsetHeight + tooltip.clientTop;
//	let tooltipTop = parentTop - arrow.offsetHeight - tooltip.clientHeight - tooltip.clientTop;

	if (tooltipLeft < 0)
	{
		arrowLeft += tooltipLeft;
		tooltipLeft = 0;
	}

	tooltip.style.left = tooltipLeft + 'px';
	tooltip.style.top = tooltipTop + 'px';
	arrow.style.left = arrowLeft + 'px';
}
function toggleTooltip(event)
{
	const toggle = event.currentTarget;
	const tooltip = toggle.previousSibling;

	if (activeTooltip) {
		const activeToggle = activeTooltip.nextSibling;
		activeToggle.firstChild.nodeValue = closedIcon;
		activeTooltip.style.display = '';

		if (tooltip === activeTooltip) {
			activeTooltip = undefined;
			return false;
		}
	}

	activeTooltip = tooltip;
	toggle.firstChild.nodeValue = openIcon;
	positionTooltip(tooltip, toggle);

	return false;
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
function enableTooltips(element, openOnClick=false)
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
		if (openOnClick) {
			const toggle = document.createElement('div');
			toggle.className = 'tooltipToggle';
			toggle.appendChild(document.createTextNode(closedIcon));
			toggle.addEventListener('click', toggleTooltip);
			parent.insertBefore(toggle, tooltip.nextSibling);
		} else {
			parent.addEventListener('mouseenter', showTooltip);
			parent.addEventListener('mouseleave', hideTooltip);
		}
		tooltip.tooltipEnabled = true;
	}
}
	window.addEventListener('DOMContentLoaded', () => enableTooltips(document.body));
	return enableTooltips;
})();
