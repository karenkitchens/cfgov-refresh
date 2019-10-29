import updateExpandableButtonText from './expandables';

const CHECKLIST_GROUP_SELECTOR = 'm-checklist-group';
const PRINT_BUTTON_SELECTOR = 'js-cbg-print';

const PRINT_CONTAINER = 'cbg-print-paper';
const GOALS_TABLE_BODY_SELECTOR = 'cbg-print-goals-body';
const NEXT_STEPS_TABLE_BODY_SELECTOR = 'cbg-next-steps-body';

const MAX_SELECTED = 3;
let selectedItems = [];

function isMaxItemsSelected() {
  return selectedItems.length === MAX_SELECTED;
}

function addSelected( item ) {
  selectedItems.push( item );
}

function removeSelected( item ) {
  const copy = selectedItems.slice();

  copy.splice( selectedItems.indexOf( item ), 1 );

  selectedItems = copy;
}

function elementToUncheck( valueToUncheck ) {
  return function uncheckCheckbox() {
    const selector = `input[value="${ valueToUncheck }"]`;
    const inputToUncheck = checklistContainer.querySelector( selector );
    inputToUncheck.checked = '';
  };
}

function isSelected( checkbox ) {
  return checkbox.checked;
}

function handleCheckListItemSelect( event ) {
  const target = event.target;

  if ( target.tagName === 'INPUT' ) {
    const selectedItem = target.value;

    if ( isSelected( target ) ) {
      if ( isMaxItemsSelected() ) {
        const lastSelected = selectedItems[selectedItems.length - 1];
        const uncheckCheckboxFn = elementToUncheck( lastSelected );

        removeSelected( lastSelected );

        /* the browser could schedule a repaint during uncheck op, so
           schedule it to happen at the beginning of the next
           stack frame */
        setTimeout( uncheckCheckboxFn, 0 );
      }
      addSelected( selectedItem );
    } else {
      removeSelected( selectedItem );
    }
  }
}

function filterChecklistItems( toExclude ) {
  const checklistKeys = Object.keys( checklistLookup );

  return checklistKeys
    .filter( key => toExclude.indexOf( key ) === -1 );
}

function buildTableBodyRows( content ) {
  const fragment = document.createDocumentFragment();
  const temp = document.createElement( 'table' );
  const tempBody = document.createElement( 'tbody' );

  temp.appendChild( tempBody );
  temp.innerHTML = content;

  const rows = Array.prototype.slice.call( temp.querySelectorAll( 'tr' ) );

  rows.forEach( row => fragment.appendChild( row ) );

  return fragment;
}

function handlePrintChecklist() {
  document.querySelector( `.${ PRINT_CONTAINER }` ).classList.remove( 'u-hidden' );

  const goalsTableContent = selectedItems.reduce( ( memo, item ) => {
    const checkListItem = checkbox( item );
    const checklistItemDetail = `<p>${ checklistLookup[item] }</p>`;
    const row = `
      <tr>
        <td>${ checkListItem }</td>
        <td>${ checklistItemDetail }</td>
      </tr>
    `;

    return `${ memo }${ row }`;
  }, '' );
  const goalsTableFragment = buildTableBodyRows( goalsTableContent );

  document.querySelector( `.${ GOALS_TABLE_BODY_SELECTOR }` ).appendChild( goalsTableFragment );

  const remainingItems = filterChecklistItems( selectedItems );
  const nextStepsTableContent = remainingItems.reduce( ( memo, item ) => {
    const checkListItem = checkbox( item );
    const row = `<tr><td>${ checkListItem }</td></tr>`;

    return `${ memo }${ row }`;
  }, '' );
  const nextStepsTableFragment = buildTableBodyRows( nextStepsTableContent );

  document.querySelector( `.${ NEXT_STEPS_TABLE_BODY_SELECTOR }` ).appendChild( nextStepsTableFragment );

  if ( isMaxItemsSelected() ) {
    printButton.removeEventListener( 'click', handlePrintChecklist );
  }
}

const cbgJSONEl = document.getElementById( 'car-buying-guide-json' );
const cbgList = JSON.parse( cbgJSONEl.innerHTML );
const checklistLookup = cbgList.reduce( ( memo, element ) => {
  memo[element.item] = element.details;

  return memo;
}, {} );

const checklistContainer = document.querySelector( `.${ CHECKLIST_GROUP_SELECTOR }` );
checklistContainer.addEventListener( 'click', handleCheckListItemSelect );

const printButton = document.querySelector( `.${ PRINT_BUTTON_SELECTOR }` );
printButton.addEventListener( 'click', handlePrintChecklist );


function checkbox( id ) {
  return `
    <div class="m-form-field m-form-field__checkbox">
      <input class="a-checkbox" type="checkbox" id="${ id }" name="${ id }">
      <label class="a-label" for="${ id }">
        <span>${ id }</span>
      </label>
    </div>
  `;
}

updateExpandableButtonText();
