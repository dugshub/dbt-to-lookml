import { useState, useMemo } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'

interface GroupedListProps<T> {
  items: T[]
  groupBy: (item: T) => string | undefined
  renderItem: (item: T) => React.ReactNode
  emptyMessage?: string
}

interface GroupNode<T> {
  name: string
  items: T[]
  children: Map<string, GroupNode<T>>
}

function buildTree<T>(
  items: T[],
  getGroup: (item: T) => string | undefined
): GroupNode<T> {
  const root: GroupNode<T> = { name: 'root', items: [], children: new Map() }

  for (const item of items) {
    const group = getGroup(item)
    if (!group) {
      root.items.push(item)
      continue
    }

    const parts = group.split('.')
    let current = root

    for (const part of parts) {
      if (!current.children.has(part)) {
        current.children.set(part, { name: part, items: [], children: new Map() })
      }
      current = current.children.get(part)!
    }

    current.items.push(item)
  }

  return root
}

function GroupSection<T>({
  node,
  depth,
  renderItem,
  defaultExpanded = true,
}: {
  node: GroupNode<T>
  depth: number
  renderItem: (item: T) => React.ReactNode
  defaultExpanded?: boolean
}) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const hasChildren = node.children.size > 0 || node.items.length > 0
  const totalItems = countItems(node)

  if (!hasChildren) return null

  const colors = [
    'border-blue-500/30 bg-blue-500/5',
    'border-purple-500/30 bg-purple-500/5',
    'border-green-500/30 bg-green-500/5',
  ]
  const colorClass = colors[depth % colors.length]

  return (
    <div className={depth > 0 ? `border-l-2 ${colorClass} ml-2 pl-3 my-2` : ''}>
      {node.name !== 'root' && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 py-2 text-sm font-medium text-gray-300 hover:text-white w-full text-left"
        >
          {expanded ? (
            <ChevronDown size={16} className="text-gray-500" />
          ) : (
            <ChevronRight size={16} className="text-gray-500" />
          )}
          <span>{node.name}</span>
          <span className="text-xs text-gray-500">({totalItems})</span>
        </button>
      )}

      {expanded && (
        <>
          {/* Render child groups */}
          {Array.from(node.children.entries())
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([name, child]) => (
              <GroupSection
                key={name}
                node={child}
                depth={depth + 1}
                renderItem={renderItem}
                defaultExpanded={depth < 1}
              />
            ))}

          {/* Render items at this level */}
          {node.items.length > 0 && (
            <div className={depth > 0 ? 'ml-6' : ''}>
              {node.items.map((item, i) => (
                <div key={i}>{renderItem(item)}</div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}

function countItems<T>(node: GroupNode<T>): number {
  let count = node.items.length
  for (const child of node.children.values()) {
    count += countItems(child)
  }
  return count
}

export function GroupedList<T>({
  items,
  groupBy,
  renderItem,
  emptyMessage = 'No items',
}: GroupedListProps<T>) {
  const tree = useMemo(() => buildTree(items, groupBy), [items, groupBy])

  if (items.length === 0) {
    return <p className="text-gray-500 text-sm py-4">{emptyMessage}</p>
  }

  return (
    <div>
      <GroupSection node={tree} depth={0} renderItem={renderItem} />
    </div>
  )
}
