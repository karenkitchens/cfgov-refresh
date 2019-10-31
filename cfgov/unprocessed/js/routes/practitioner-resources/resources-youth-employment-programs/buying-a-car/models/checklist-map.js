import { assign } from '../../../../../../apps/youth-employment-success/js/util';

const CONTENT_TYPE = 'expandable_group';

function isExpandable( item ) {
  return item.type === CONTENT_TYPE;
}

function flattenExpandableGroups( flattened, group ) {
  return flattened.concat( group.value.expandables );
}

function addContentToLookup( lookup, expandable ) {
  lookup[expandable.label.trim()] = expandable.content[0].value;
  return lookup;
}

function checklistMap( list ) {
  const lookup = list
    .filter( isExpandable )
    .reduce( flattenExpandableGroups, [] )
    .reduce( addContentToLookup, {} );

  function checklist() {
    return assign( {}, lookup );
  }

  function filterKeysBy( predicate ) {
    const keys = Object.keys( lookup );

    return keys.filter( predicate );
  }

  function get( key ) {
    return lookup[key];
  }

  return {
    checklist,
    get,
    filterKeysBy
  };
}

export default checklistMap;
