import checkbox from './templates/checkbox';
import paragraph from './templates/paragraph';
import tableRow from './templates/table-row';
import selectedItems from './models/selected-items';
import checklistMap from './models/checklist-map';
import updateExpandableButtonText from './expandables';
import printButtonView from '../../../../../apps/youth-employment-success/js/views/print-button'

const CHECKLIST_GROUP_SELECTOR = 'm-checklist-group';
const PRINT_BUTTON_SELECTOR = 'js-cbg-print';

const PRINT_CONTAINER = 'cbg-print-paper';
const GOALS_TABLE_BODY_SELECTOR = 'cbg-print-goals-body';
const NEXT_STEPS_TABLE_BODY_SELECTOR = 'cbg-next-steps-body';

const cbgJSONEl = document.getElementById( 'car-buying-guide-json' );
const cbgList = JSON.parse( cbgJSONEl.innerHTML );

const items = selectedItems();
const checklistLookup = checklistMap(cbgList);

printButtonView(
  document.querySelector( `.${ PRINT_BUTTON_SELECTOR }` ), {
    btnClass: PRINT_BUTTON_SELECTOR,
    onBeforePrint: handlePrintChecklist
  }
).init();

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
      if ( items.isMaxItemsSelected() ) {
        const lastSelected = items.getLast();
        const uncheckCheckboxFn = elementToUncheck( lastSelected );

        items.removeSelected( lastSelected );

        /* the browser could schedule a repaint during uncheck op, so
           schedule it to happen at the beginning of the next
           stack frame */
        setTimeout( uncheckCheckboxFn, 0 );
      }
      items.addSelected( selectedItem );
    } else {
      items.removeSelected( selectedItem );
    }
  }
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
  const goalsTableContent = items.elements().reduce( ( memo, item ) => {
    const checklistItem = checkbox( item );
    const checklistItemDetail = paragraph(checklistLookup.get(item));
    const row = tableRow([
      checklistItem,
      checklistItemDetail
    ]);

    return `${ memo }${ row }`;
  }, '' );

  const goalsTableFragment = buildTableBodyRows( goalsTableContent );

  document.querySelector( `.${ GOALS_TABLE_BODY_SELECTOR }` ).appendChild( goalsTableFragment );

  const remainingItems = checklistLookup.filterKeysBy((key) => {
    return items.elements().indexOf( key ) === -1 ;
  });
  const nextStepsTableContent = remainingItems.reduce( ( memo, item ) => {
    const checkListItem = checkbox( item );
    const row = tableRow(checkListItem);

    return `${ memo }${ row }`;
  }, '' );
  const nextStepsTableFragment = buildTableBodyRows( nextStepsTableContent );

  document.querySelector( `.${ NEXT_STEPS_TABLE_BODY_SELECTOR }` ).appendChild( nextStepsTableFragment );
}

const checklistContainer = document.querySelector( `.${ CHECKLIST_GROUP_SELECTOR }` );
checklistContainer.addEventListener( 'click', handleCheckListItemSelect );

updateExpandableButtonText();
