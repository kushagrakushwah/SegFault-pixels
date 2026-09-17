import graphviz

dot = graphviz.Digraph(comment='The Round Table', node_attr={'colorscheme':'set312'}, graph_attr={'rankdir':'LR'})
dot.node('A', 'King Arthur', color = '1') 
dot.node('B', 'Sir Bedevere the Wise', color = '2')
dot.node('L', 'Sir Lancelot the Brave', color = '3')

dot.edges(['AB', 'AL'])
dot.edge('B', 'L', constraint='false')

print(dot.source)

dot.render('./round-table', format='svg', cleanup=True, engine='dot', view=True)