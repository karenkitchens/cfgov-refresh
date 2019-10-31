import checkbox from './templates/checkbox';
import checklistGroupView from './views/checklist-group';
import checklistMap from './models/checklist-map';
import error from './views/error';
import printButtonView from '../../../../../apps/youth-employment-success/js/views/print-button';
import printTableView from './views/print-table';
import selectedItems from './models/selected-items';
import updateExpandableButtonText from './expandables';


const CHECKLIST_GROUP_SELECTOR = 'm-checklist-group';
const PRINT_BUTTON_SELECTOR = 'js-cbg-print';

const GOALS_TABLE_SELECTOR = 'cbg-print-goals';
const NEXT_STEPS_TABLE_SELECTOR = 'cbg-print-next-steps';

const cbgJSONEl = document.getElementById( 'car-buying-guide-json' );
const cbgChecklistData = JSON.parse( cbgJSONEl.innerHTML );

const items = selectedItems( { maxElements: 5 } );
const checklistLookup = checklistMap( cbgChecklistData );

const errorView = error( document.querySelector( `.${ error.CONTAINER }` ) );

updateExpandableButtonText();

checklistGroupView(
  document.querySelector( `.${ CHECKLIST_GROUP_SELECTOR }` ), {
    selectedItems: items
  }
).init();

printButtonView(
  document.querySelector( `.${ PRINT_BUTTON_SELECTOR }` ), {
    btnClass: PRINT_BUTTON_SELECTOR,
    onBeforePrint: updateTableView,
    onClick: handlePrintChecklist
  }
).init();

const goalsTableView = printTableView(
  document.querySelector( `.${ GOALS_TABLE_SELECTOR }` )
);
const nextStepsTableView = printTableView(
  document.querySelector( `.${ NEXT_STEPS_TABLE_SELECTOR }` )
);

function handlePrintChecklist( event, printFn ) {
  if ( items.isMinItemsSelected() ) {
    errorView.render( false );
    printFn( event );
  } else {
    errorView.render( true );
    event.preventDefault();
    event.stopImmediatePropagation();
  }
}

function updateTableView() {
  const selectedChecklistItems = items.elements();
  const goalsTableContent = selectedChecklistItems.reduce( ( memo, item ) => {
    const checklistItem = checkbox( item );
    const checklistItemDetail = checklistLookup.get( item );

    memo.push( [ checklistItem, checklistItemDetail ] );

    return memo;
  }, [] );

  goalsTableView.render( goalsTableContent );

  const remainingItems = checklistLookup.filterKeysBy( key => selectedChecklistItems.indexOf( key ) === -1 );
  const nextStepsTableContent = remainingItems.map( item => checkbox( item ) );

  nextStepsTableView.render( nextStepsTableContent );
}
