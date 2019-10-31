import { assign } from '../../../../../../apps/youth-employment-success/js/util';

function checklistMap(list) {
  const lookup = list.reduce( ( memo, { item, details } ) => {
    memo[item] = details;
  
    return memo;
  }, {} );

  function checklist() {
    return assign({}, lookup);
  }

  function filterKeysBy(predicate) {
    const keys = Object.keys(lookup);

    return keys.filter(predicate);
  }

  function get(key) {
    return lookup[key];
  }

  return {
    checklist,
    get,
    filterKeysBy
  };
}

export default checklistMap;
