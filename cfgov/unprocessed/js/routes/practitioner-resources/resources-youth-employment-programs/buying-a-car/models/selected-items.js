/**
 * Data structure to manipulate a list of `maxElements` elements
 * @param {Object} props The properties that configure this data structure
 * @oaram {Number} maxElements The maximum number of elements the data structure can hold
 * @returns {Object} The public methods of this data structure
 */
function selectedItems({ maxElements = 3 } = {}) {
  let items = [];

  function isMaxItemsSelected() {
    return items.length === maxElements;
  }
  
  function add( item ) {
    if (!isMaxItemsSelected()) {
      items.push( item );
    }
  }
  
  function remove( item ) {
    const copy = items.slice();
  
    copy.splice( items.indexOf( item ), 1 );
  
    items = copy;
  }

  function length() {
    return items.length;
  }

  function elements() {
    return items;
  }

  function getHead() {
    return items[0];
  }

  function getLast() {
    return items[items.length - 1];
  }

  return {
    add,
    elements,
    getHead,
    getLast,
    isMaxItemsSelected,
    length,
    remove
  };
}

export default selectedItems;
