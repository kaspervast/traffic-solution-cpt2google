export type Segment={id:string;name:string;direction:string;geometry:number[][];lanes:number;free_flow_speed_kph:number;current_speed_kph?:number;traffic_provenance?:string;mapping_confidence:number;provenance:string;custom?:boolean};
export type Metric={name:string;baseline:number;proposal:number;delta:number;delta_percent:number;ci95:number;unit:string;improved:boolean};
