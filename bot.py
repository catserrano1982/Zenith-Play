function doPost(e) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheetVideos = ss.getSheetByName("Videos") || ss.getSheets()[0];
    var data = JSON.parse(e.postData.contents);
    
    // NUEVA LÓGICA: Actualizar la paginación desde el panel admin
    if (data.action === "update_config") {
      var sheetConfig = ss.getSheetByName("Configuracion");
      if (sheetConfig) {
        sheetConfig.getRange("B1").setValue(data.per_page);
        return ContentService.createTextOutput(JSON.stringify({"status": "success", "message": "Paginación actualizada"}))
          .setMimeType(ContentService.MimeType.JSON);
      }
    }

    // Lógica para actualizar portada
    if (data.action === "update_cover") {
      var dataRange = sheetVideos.getDataRange().getValues();
      var updated = false;
      
      for (var i = 1; i < dataRange.length; i++) {
        if (String(dataRange[i][0]) === String(data.id)) {
          // Actualiza la celda en la columna D (índice 4)
          sheetVideos.getRange(i + 1, 4).setValue(data.portada);
          updated = true;
          break;
        }
      }
      
      if (updated) {
        return ContentService.createTextOutput(JSON.stringify({"status": "success", "message": "Portada actualizada"}))
          .setMimeType(ContentService.MimeType.JSON);
      } else {
        return ContentService.createTextOutput(JSON.stringify({"status": "error", "message": "Video no encontrado"}))
          .setMimeType(ContentService.MimeType.JSON);
      }
    }

    // Lógica normal: Añadir video nuevo
    sheetVideos.appendRow([data.id, data.titulo, data.enlace, data.portada, data.fecha]);
    return ContentService.createTextOutput(JSON.stringify({"status": "success"}))
      .setMimeType(ContentService.MimeType.JSON);
      
  } catch(error) {
    return ContentService.createTextOutput(JSON.stringify({"status": "error", "message": error.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sheetVideos = ss.getSheetByName("Videos") || ss.getSheets()[0];
    var sheetConfig = ss.getSheetByName("Configuracion");
    
    // 1. Leer los Videos
    var data = sheetVideos.getDataRange().getValues();
    var headers = data[0];
    var result = [];
    
    for (var i = 1; i < data.length; i++) {
      var row = data[i];
      var obj = {};
      for (var j = 0; j < headers.length; j++) {
        obj[headers[j]] = row[j];
      }
      result.push(obj);
    }
    
    // 2. Leer la Configuración de Paginación
    var perPage = 12; // Valor por defecto por si falla
    if (sheetConfig) {
      var configVal = sheetConfig.getRange("B1").getValue();
      if (!isNaN(configVal) && configVal > 0) {
        perPage = parseInt(configVal);
      }
    }
    
    // 3. Enviar todo a Render
    return ContentService.createTextOutput(JSON.stringify({
      "status": "success", 
      "data": result,
      "config": {
        "per_page": perPage
      }
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch(error) {
    return ContentService.createTextOutput(JSON.stringify({"status": "error", "message": error.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
