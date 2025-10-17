# export_csv_arXiv_artigos
Script para exportação de de CSV de artigos por meio da sintaxe do Command Search do IEEEXplore

(
  "All Metadata":"computer vision" OR
  "All Metadata":"video analysis" OR
  "All Metadata":"video-based"
)
AND
(
  "All Metadata":"student engagement" OR
  "All Metadata":"learning engagement" OR
  "All Metadata":"attention estimation"
)
AND
(
  "All Metadata":"e-learning" OR
  "All Metadata":"online learning" OR
  "All Metadata":"distance education" OR
  "All Metadata":"MOOC"
)
AND
(
  ("All Metadata":"CNN" OR "All Metadata":"convolutional neural network" OR
   "All Metadata":"transformer" OR "All Metadata":"LSTM")
  OR
  ("All Metadata":"performance evaluation" OR "All Metadata":"accuracy" OR
   "All Metadata":"effectiveness" OR "All Metadata":"real-world" OR
   "All Metadata":"in the wild")
)

