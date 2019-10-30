/**
 * Data structure to manipulate a list of `maxElements` elements
 * @param {Object} props The properties that configure this data structure
 * @oaram {Number} maxElements The maximum number of elements the data structure can hold
 * @returns {Object} The public methods of this data structure
 */
function selectedItems({ maxElements = 3 }) {
  let items = [];

  function isMaxItemsSelected() {
    return items.length === maxElements;
  }
  
  function addSelected( item ) {
    if (!isMaxItemsSelected()) {
      items.push( item );
    }
  }
  
  function removeSelected( item ) {
    const copy = items.slice();
  
    copy.splice( items.indexOf( item ), 1 );
  
    items = copy;
  }

  return {
    addSelected,
    isMaxItemsSelected,
    removeSelected
  };
}

export default selectedItems;
