import checkbox from './templates/checkbox';
import checklistGroupView from './checklist-group';
import checklistMap from './models/checklist-map';
import paragraph from './templates/paragraph';
import printButtonView from '../../../../../apps/youth-employment-success/js/views/print-button'
import selectedItems from './models/selected-items';
import tableRow from './templates/table-row';
import updateExpandableButtonText from './expandables';


const CHECKLIST_GROUP_SELECTOR = 'm-checklist-group';
const PRINT_BUTTON_SELECTOR = 'js-cbg-print';

const GOALS_TABLE_BODY_SELECTOR = 'cbg-print-goals-body';
const NEXT_STEPS_TABLE_BODY_SELECTOR = 'cbg-next-steps-body';

const cbgJSONEl = document.getElementById( 'car-buying-guide-json' );
const cbgChecklistData = JSON.parse( cbgJSONEl.innerHTML );

const items = selectedItems();
const checklistLookup = checklistMap(cbgChecklistData);

printButtonView(
  document.querySelector( `.${ PRINT_BUTTON_SELECTOR }` ), {
    btnClass: PRINT_BUTTON_SELECTOR,
    onBeforePrint: handlePrintChecklist
  }
).init();

checklistGroupView(
  document.querySelector( `.${ CHECKLIST_GROUP_SELECTOR }` ), {
    selectedItems: items
  }
).init();

updateExpandableButtonText();


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
  const checklistDataElements = items.elements();
  const goalsTableContent = checklistDataElements.reduce( ( memo, item ) => {
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
    return checklistDataElements.indexOf( key ) === -1 ;
  });
  const nextStepsTableContent = remainingItems.reduce( ( memo, item ) => {
    const checkListItem = checkbox( item );
    const row = tableRow(checkListItem);

    return `${ memo }${ row }`;
  }, '' );
  const nextStepsTableFragment = buildTableBodyRows( nextStepsTableContent );

  document.querySelector( `.${ NEXT_STEPS_TABLE_BODY_SELECTOR }` ).appendChild( nextStepsTableFragment );
}
