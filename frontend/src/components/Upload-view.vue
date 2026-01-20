<template>
  <div class="upload-container">
    <h2>Upload Your Data (CSV Only)</h2>

    <!-- 提示信息 -->
    <p class="instruction-text">
      Please upload your data file via the button below (note that only .csv files are accepted).<br>
      Your CSV file should contain two columns:
      1) interview questions or their types/categories, and
      2) participants' verbatim responses (raw text). <br>
      On the next page, you will upload your theoretical framework.
    </p>

    <!-- 文件选择 -->
    <input type="file" accept=".csv" @change="handleFileUpload" />

    <!-- CSV 预览表格 -->
    <div v-if="csvData.length" class="preview-section">
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th v-for="(col, index) in columns" :key="index">
                {{ col }}
              </th>
            </tr>
          </thead>
          <tbody>
            <!-- 只显示前5行做预览 -->
            <tr v-for="(row, rowIndex) in csvData" :key="rowIndex">
              <td v-for="(col, colIndex) in columns" :key="colIndex">
                {{ row[col] }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 选择列对应关系 -->
    <div v-if="columns.length" class="column-mapping">
      <h4>Please manually select the following two columns:</h4>
      <div class="column-selection">
        <label>Question Type:</label>
        <select v-model="selectedQuestionType">
          <option value="" disabled>Please select the column</option>
          <option v-for="(col, index) in columns" :key="index" :value="col">
            {{ col }}
          </option>
        </select>
      </div>

      <div class="column-selection">
        <label>Original Text:</label>
        <select v-model="selectedOriginalText">
          <option value="" disabled>Please select the column</option>
          <option v-for="(col, index) in columns" :key="index" :value="col">
            {{ col }}
          </option>
        </select>
      </div>

    </div>

    <!-- 错误信息展示 -->
    <div v-if="error" class="error-message">
      {{ error }}
    </div>

    <!-- Confirm 按钮固定在页面右下角 -->
    <div class="confirm-button-container" v-if="fileUploaded">
      <button @click="handleConfirm">Confirm</button>
    </div>
  </div>
</template>

<script>
import Papa from 'papaparse';

export default {
  name: 'UploadView',
  data() {
    return {
      userId: '',
      file: null,               // 用户选择的文件对象
      columns: [],             // CSV的列名数组
      csvData: [],             // CSV所有行的数据
      selectedQuestionType: '',// 用户选定的 question_type 列
      selectedOriginalText: '',// 用户选定的 original_text 列
      error: '',               // 错误提示信息
      fileUploaded: false      // 是否已上传文件（默认 false）
    };
  },

  mounted() {
    this.userId = this.$route.query.userId; // 获取传递的 userId
  },

  methods: {
    // 处理文件上传
    handleFileUpload(e) {
      this.error = '';
      const file = e.target.files[0];
      if (!file) {
        return;
      }
      // 校验文件类型是否为 CSV
      if (!file.name.toLowerCase().endsWith('.csv')) {
        this.error = 'Please upload a CSV file';
        return;
      }
      // 使用 Papa Parse 进行 CSV 文件解析
      Papa.parse(file, {
        header: true,            // 第一行作为 header
        skipEmptyLines: true,    // 跳过空行
        complete: (results) => {
          if (results.errors && results.errors.length) {
            this.error = 'An error occurred while parsing CSV. Please check the file format';
            console.error(results.errors);
            return;
          }
          // 将解析后的数据存储
          this.csvData = results.data;
          // 解析 meta.fields 可以得到 CSV 的所有列名
          this.columns = results.meta.fields || [];
          this.fileUploaded = true; // 标记文件已上传
        }
      });
    },
    // 用户确认选择结果的方法
    handleConfirm() {
      if (!this.selectedQuestionType || !this.selectedOriginalText) {
        this.error = 'Please select the corresponding two columns first';
        return;
      }
      // 这里可以根据业务需求，执行进一步操作
      // 例如将所选列的信息提交到后端，或跳转页面等
      console.log('question_type列:', this.selectedQuestionType);
      console.log('original_text列:', this.selectedOriginalText);

      // 示例：如果需要跳转到其他页面：
      this.$router.push({
        name: 'DrawingBoard',
        query: {
          userId: this.userId,
          question_type: this.selectedQuestionType,
          original_text: this.selectedOriginalText,
        }
      });
    }
  }
};
</script>

<style scoped>
.upload-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-top: 20px;
  margin-bottom: 20px;
}

input[type="file"] {
  margin-bottom: 20px;
}

/* 提示文本样式 */
.instruction-text {
  max-width: 80%;
  text-align: center;
  font-size: 16px;
  color: #333;
  margin-bottom: 15px;
}

.preview-section {
  width: 90%;
  max-height: 400px;
  max-width: 1600px;
  overflow: auto;
}

.table-wrapper {
  max-height: 400px;
  overflow: auto;
  border: 1px solid #ddd;
}

table {
  width: 100%;
  table-layout: auto;
  border-collapse: collapse;
  word-wrap: break-word; /* 允许自动换行 */
  white-space: normal; /* 防止文本换行 */
}

th, td {
  border: 1px solid #ddd;
  padding: 12px;
  text-align: left;
  vertical-align: top;
  word-wrap: break-word;
  white-space: normal;
  min-width: 200px;
}

/* 选择列映射 */
.column-mapping {
  margin-top: 30px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.column-selection {
  display: grid;
  grid-template-columns: 150px auto; /* 第一列固定宽度，第二列自适应 */
  align-items: center;
  margin-bottom: 15px;
  gap: 10px;
}

.column-selection label {
  font-size: 16px;
  font-weight: bold;
  text-align: right; /* 让 label 右对齐 */
  white-space: nowrap; /* 避免 label 换行 */
}

.confirm-button-container {
  position: fixed;
  bottom: 20px;
  right: 20px;
  display: flex;
  justify-content: flex-end;
  width: 100%;
  padding: 20px;
}

.column-selection select {
  padding: 12px;
  font-size: 16px;
  border: 1px solid #ccc;
  border-radius: 5px;
  cursor: pointer;
  width: 100%; /* 让选择框填满 grid 单元 */
}

/* 间距增加 */
.column-mapping div {
  margin-bottom: 20px; /* 增加每个选择框的间距 */
}

.confirm-button-container button {
  background-color: #007bff;
  color: white;
  font-size: 18px;
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.3s ease;
  box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
  max-width: 200px; /* 限制最大宽度 */
  width: auto; /* 让宽度自适应内容 */
}

.confirm-button-container button:hover {
  background-color: #0056b3;
}

.error-message {
  color: red;
  margin-top: 10px;
}
</style>
