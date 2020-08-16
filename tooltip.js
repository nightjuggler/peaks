/* globals document, window */
/* exported enableTooltips */

const enableTooltips = (function() {
'use strict';

let activeTooltip;

const closedIcon = '\u25C4\uFE0E'; // black left-pointing pointer
const openIcon = '\u25B2'; // black up-pointing triangle

function positionTooltip(tooltip, host)
{
	tooltip.style.display = 'block';
	activeTooltip = tooltip;

	const arrow = tooltip.lastElementChild;

	if (!host) host = tooltip.parentElement;

	let parent = tooltip.offsetParent;
	let parentStyle;

	while ((parentStyle = window.getComputedStyle(parent)).position === 'static' && parent.parentElement)
		parent = parent.parentElement;

	const borderLeft = +parentStyle.borderLeftWidth.slice(0, -2); // strip 'px'
	const borderTop = +parentStyle.borderTopWidth.slice(0, -2); // strip 'px'

	const hostBox = host.getBoundingClientRect();
	const parentBox = parent.getBoundingClientRect();

	const offsetLeft = hostBox.left - (parentBox.left + borderLeft);
	const offsetTop = hostBox.top - (parentBox.top + borderTop);

	let tooltipLeft = offsetLeft + (host.offsetWidth - tooltip.offsetWidth) / 2;
	let tooltipTop = offsetTop - arrow.offsetHeight - tooltip.offsetHeight + tooltip.clientTop;
	let arrowLeft = (tooltip.clientWidth - arrow.offsetWidth) / 2;

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

	toggle.firstChild.nodeValue = openIcon;
	positionTooltip(tooltip, toggle);
	return false;
}
function showTooltip(event)
{
	const tooltip = event.currentTarget.getElementsByClassName('tooltip')[0];
	positionTooltip(tooltip);
	return false;
}
function hideTooltip(event)
{
	const tooltip = event.currentTarget.getElementsByClassName('tooltip')[0];
	tooltip.style.display = '';
	if (tooltip === activeTooltip)
		activeTooltip = undefined;
	return false;
}
function enableTooltips(element, openOnClick=false)
{
	const mode = openOnClick ? 1 : 2;

	for (const tooltip of element.getElementsByClassName('tooltip'))
	{
		const parent = tooltip.parentElement;

		if (tooltip.tooltipMode) {
			if (tooltip.tooltipMode === mode) continue;
			if (tooltip === activeTooltip) {
				tooltip.style.display = '';
				activeTooltip = undefined;
			}
			if (openOnClick) {
				parent.removeEventListener('mouseenter', showTooltip);
				parent.removeEventListener('mouseleave', hideTooltip);
			} else
				parent.removeChild(tooltip.nextSibling);
		} else {
			const arrowDiv = document.createElement('div');
			const arrow1 = document.createElement('div');
			const arrow2 = document.createElement('div');

			arrowDiv.className = 'tooltipArrowDiv';
			arrow1.className = 'tooltipArrow1';
			arrow2.className = 'tooltipArrow2';

			arrowDiv.appendChild(arrow1);
			arrowDiv.appendChild(arrow2);
			tooltip.appendChild(arrowDiv);
		}

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
		tooltip.tooltipMode = mode;
	}
}
	window.addEventListener('DOMContentLoaded', () => enableTooltips(document.body));
	return enableTooltips;
})();
