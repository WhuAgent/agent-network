<template>
  <div>
    <el-upload
      ref="file_list"
      action=""
      :limit="1"
      :on-exceed="handleExceed"
      :on-change="load_file"
      :auto-upload="false"
    >
    <el-button type="primary">select file</el-button>
    </el-upload>
    <el-tabs :tab-position="tabPosition" style="height: 200px" class="demo-tabs">
      <el-tab-pane v-for="instance in all_instance" :label="instance">
        {{ instance }}
      </el-tab-pane>
    </el-tabs>
    <div v-for="trace in trace_data" style="margin: 5px;">
      <el-card
        :style="{ backgroundColor: color[trace.instance] }"
      >
        <h3>{{ trace.instance }} - {{ trace.role }}</h3>
        <div v-html="trace.content"></div>
      </el-card>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, reactive } from 'vue';
import { genFileId, TabsInstance } from 'element-plus';
import type { UploadInstance, UploadProps, UploadRawFile } from 'element-plus';
import MarkdownIt from 'markdown-it';
import mk from 'markdown-it-katex';

export default defineComponent({
  setup() {
    const file_list = ref<UploadInstance>();
    const trace_data = ref<any[]>();
    const catogrized_data = reactive<{ [key: string]: any[] }>({});
    const color = reactive<{ [kye: string]: string }>({
      "Agent-network": "#909399",
      "Calculator": "#67C23A",
      "Thinker": "#409EFF",
      "Judger": "#E6A23C"
    })

    const all_instance = ref<string[]>(["All"]);
    const tabPosition = ref<TabsInstance['tabPosition']>('left')

    const handleExceed: UploadProps['onExceed'] = (files) => {
      file_list.value!.clearFiles()
      const file = files[0] as UploadRawFile
      file.uid = genFileId()
      file_list.value!.handleStart(file)
    };

    const load_file = (file: UploadProps["onChange"]) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        if (typeof e.target.result  === "string") {
          trace_data.value = JSON.parse(e.target.result);
          trace_data.value.forEach(trace => {
            trace["content"] = render_md(trace["content"]);
          });
          console.log(trace_data.value);
          catogrize_trace();
        }
      };

      reader.readAsText(file.raw!);
    };

    const catogrize_trace = () => {
      trace_data.value.forEach(trace => {
        if (trace["instance"] in catogrized_data) {
          catogrized_data[trace["instance"]].push(trace);
        } else {  
          catogrized_data[trace["instance"]] = [trace];
          all_instance.value.push(trace["instance"]);
          console.log(all_instance.value);
        }
      });
      console.log(catogrized_data.value);
    };

    const render_md = (content: string) => {
      const md = new MarkdownIt();
      md.use(mk);
      return md.render(content);
    }

    return {
      file_list,
      trace_data,
      catogrized_data,
      color,
      all_instance,
      tabPosition,
      handleExceed,
      load_file,
      catogrize_trace,
      render_md
    };
  },
});
</script>